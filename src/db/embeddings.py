"""Read/write article embeddings and the event id derived from them.

Split from src/db/events.py, which is read-only display queries. This module is
the only writer of articles.title_embedding and articles.event_id.

The vector round-trip is plain text, not pgvector's binary protocol: psycopg
has no adapter registered for the vector type, and pgvector accepts and returns
the literal '[0.1,0.2,...]'. At 384 dimensions written once per article that is
not worth a dependency.
"""

from __future__ import annotations

import numpy as np

from src.analysis.embeddings import PASSAGE_LEAD_CHARS
from src.db.config import require_database_url
from src.db.connection import get_connection


def _to_literal(vector: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.6f}" for x in vector) + "]"


def iter_articles_needing_embedding(model: str, limit: int | None = None) -> list[dict]:
    """Articles with a topic label and no current vector.

    Gated on the model as well as on NULL, so changing EMBED_MODEL re-embeds the
    corpus instead of leaving two vector spaces mixed in one column - the same
    version-gate pattern the polarization lexicon uses.
    """
    require_database_url()
    query = """
        SELECT article_id, title, LEFT(COALESCE(text, ''), %s) AS lead
        FROM articles
        WHERE primary_category IS NOT NULL
          AND title IS NOT NULL
          AND (title_embedding IS NULL OR embedding_model IS DISTINCT FROM %s)
        ORDER BY first_seen_at DESC
    """
    params: list = [PASSAGE_LEAD_CHARS, model]
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]


def save_embeddings(rows: list[tuple[str, np.ndarray]], *, model: str) -> int:
    """Write vectors for the given article_ids. Returns the number written."""
    if not rows:
        return 0
    require_database_url()
    payload = [(_to_literal(vector), model, article_id) for article_id, vector in rows]
    with get_connection() as conn:
        with conn.cursor() as cur:
            # executemany so psycopg pipelines the batch; one statement per
            # article at Neon's round-trip latency is what made the polarization
            # backfill take 80 minutes before it was batched.
            cur.executemany(
                """
                UPDATE articles
                SET title_embedding = %s::vector,
                    embedding_model = %s,
                    embedded_at = NOW()
                WHERE article_id = %s
                """,
                payload,
            )
        conn.commit()
    return len(payload)


def load_embedded_articles(model: str) -> list[dict]:
    """Every article carrying a current vector, for the clustering pass."""
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT article_id, primary_category, first_seen_at,
                       title_embedding::text AS vector
                FROM articles
                WHERE title_embedding IS NOT NULL AND embedding_model = %s
                ORDER BY first_seen_at, article_id
                """,
                (model,),
            )
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    for row in rows:
        row["vector"] = np.fromstring(row["vector"].strip("[]"), sep=",", dtype=np.float32)
    return rows


def save_event_assignments(assignments: dict[str, str], *, cleared_ids: list[str]) -> None:
    """Persist event membership: article_id -> event_id.

    `cleared_ids` are articles that no longer belong to any event and must have
    a stale id removed. Both happen in one transaction, because a corpus with
    half the old clustering and half the new one is not a state any reader
    should be able to observe.
    """
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if cleared_ids:
                cur.execute(
                    """
                    UPDATE articles
                    SET event_id = NULL, event_assigned_at = NULL
                    WHERE article_id = ANY(%s)
                    """,
                    (cleared_ids,),
                )
            if assignments:
                cur.executemany(
                    """
                    UPDATE articles
                    SET event_id = %s, event_assigned_at = NOW()
                    WHERE article_id = %s
                    """,
                    [(event_id, article_id) for article_id, event_id in assignments.items()],
                )
        conn.commit()


def load_event_assignments() -> dict[str, list[str]]:
    """Stored events: event_id -> member article_ids, oldest member first.

    Empty when no embedding pass has run yet, which is the signal callers use to
    fall back to the lexical grouping.
    """
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id, article_id
                FROM articles
                WHERE event_id IS NOT NULL
                ORDER BY first_seen_at, article_id
                """
            )
            groups: dict[str, list[str]] = {}
            for event_id, article_id in cur.fetchall():
                groups.setdefault(event_id, []).append(article_id)
            return groups

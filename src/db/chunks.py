"""Read/write retrieval chunks, and the hybrid search that ranks them.

Split by concern like the rest of src/db/: this module owns `article_chunks`
and nothing else. The write half runs during ingestion; the read half —
`search_chunks` — runs on the API host and is the only query the assistant
makes against the corpus.

**The scoring happens in Postgres, not in Python.** Two reasons, and the first
is not style: CI asserts that `src.api.app` imports no numpy (see
.github/workflows/ci.yml), so there is nothing on the API host to multiply
vectors with. The second is Neon's transfer quota, which re-reading the corpus
on every request already exhausted once (ADR 0005). Ranking server-side and
returning k rows moves kilobytes where scoring client-side would move
megabytes.
"""

from __future__ import annotations

from src.db.config import require_database_url
from src.db.connection import get_connection

# Reciprocal Rank Fusion's smoothing constant, from Cormack et al. (2009), who
# reported it insensitive between roughly 20 and 100. It sets how sharply the
# top of each list outranks its tail: at k=60 the first result contributes
# 1/61 and the tenth 1/70, so a chunk that both channels rank tenth beats one
# that only the vector search ranks first.
#
# Fusing *ranks* rather than scores is the point. A cosine distance and a count
# of matched Hebrew substrings have no common scale, and any attempt to weight
# them against each other directly is a magic number with no defensible value.
RRF_K = 60

# How deep each channel searches before the two lists are fused. Larger than the
# number of chunks that reach the model, because a chunk ranked 20th by the
# vector search and 3rd lexically should still be able to win — which it cannot
# if the vector list was cut at 8.
CHANNEL_POOL = 40

# Chunks from one article that may appear in one answer's context. Without a
# cap, a long article that is genuinely on-topic contributes six near-identical
# passages and crowds out the second outlet's version of the same story — which
# for this corpus, where comparing outlets is the entire point, is the worst
# possible failure.
MAX_CHUNKS_PER_ARTICLE = 2


def save_chunks(article_id: str, chunks: list[tuple[str, int, str]]) -> int:
    """Upsert one article's chunks: (chunk_id, ordinal, text).

    Rewriting the text of an existing ordinal clears its vector, so a re-chunked
    article cannot keep serving a vector that describes the passage it used to
    hold. Chunks past the new end are deleted in the same transaction.
    """
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if chunks:
                cur.executemany(
                    """
                    INSERT INTO article_chunks (chunk_id, article_id, ordinal, text)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (article_id, ordinal) DO UPDATE
                    SET text = EXCLUDED.text,
                        embedding = CASE
                            WHEN article_chunks.text IS DISTINCT FROM EXCLUDED.text
                            THEN NULL ELSE article_chunks.embedding END,
                        embedding_model = CASE
                            WHEN article_chunks.text IS DISTINCT FROM EXCLUDED.text
                            THEN NULL ELSE article_chunks.embedding_model END
                    """,
                    [(cid, article_id, ordinal, text) for cid, ordinal, text in chunks],
                )
            cur.execute(
                "DELETE FROM article_chunks WHERE article_id = %s AND ordinal >= %s",
                (article_id, len(chunks)),
            )
        conn.commit()
    return len(chunks)


def iter_articles_needing_chunks(limit: int | None = None) -> list[dict]:
    """Articles with a body and no chunks yet.

    Gated on absence rather than on a timestamp: chunking is deterministic, so
    an article that has chunks has the right ones unless its text changed, and
    that case is handled by save_chunks overwriting in place.
    """
    require_database_url()
    query = """
        SELECT a.article_id, a.title, a.text
        FROM articles a
        WHERE LENGTH(a.text) > 0
          AND NOT EXISTS (SELECT 1 FROM article_chunks c WHERE c.article_id = a.article_id)
        ORDER BY a.first_seen_at DESC
    """
    params: list = []
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]


def iter_chunks_needing_embedding(model: str, limit: int | None = None) -> list[dict]:
    """Chunks with no current vector, newest article first.

    Gated on the model as well as on NULL, so changing EMBED_MODEL re-embeds
    rather than leaving two vector spaces mixed in one column — the same
    version-gate the event embeddings and the polarization lexicon use.
    """
    require_database_url()
    query = """
        SELECT c.chunk_id, c.text, a.title
        FROM article_chunks c
        JOIN articles a ON a.article_id = c.article_id
        WHERE c.embedding IS NULL OR c.embedding_model IS DISTINCT FROM %s
        ORDER BY a.first_seen_at DESC, c.ordinal
    """
    params: list = [model]
    if limit:
        query += " LIMIT %s"
        params.append(limit)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]


def save_chunk_embeddings(rows: list[tuple[str, str]], *, model: str) -> int:
    """Write vectors for the given chunk_ids, as pgvector literals."""
    if not rows:
        return 0
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            # executemany so psycopg pipelines the batch. One statement per
            # chunk at Neon's round-trip latency is what made an earlier
            # backfill in this codebase take 80 minutes (src/db/embeddings.py).
            cur.executemany(
                """
                UPDATE article_chunks
                SET embedding = %s::vector,
                    embedding_model = %s,
                    embedded_at = NOW()
                WHERE chunk_id = %s
                """,
                [(literal, model, chunk_id) for chunk_id, literal in rows],
            )
        conn.commit()
    return len(rows)


def count_embedded_chunks(model: str) -> int:
    """How many chunks are searchable. Zero means retrieval has nothing to
    stand on, which the assistant needs to say rather than silently answer
    from the summary statistics alone."""
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM article_chunks "
                "WHERE embedding IS NOT NULL AND embedding_model = %s",
                (model,),
            )
            return int(cur.fetchone()[0])


_RESULT_COLUMNS = """
    c.chunk_id, c.article_id, c.ordinal, c.text,
    a.source, a.title, a.canonical_url AS url, a.primary_category, a.first_seen_at,
    agg.audience_mean, agg.audience_p85, agg.num_comments
"""

_RESULT_JOINS = """
    JOIN articles a ON a.article_id = c.article_id
    LEFT JOIN LATERAL (
        SELECT audience_mean, audience_p85, num_comments
        FROM article_comments_agg
        WHERE article_id = a.article_id
        ORDER BY analyzed_at DESC
        LIMIT 1
    ) agg ON TRUE
"""


def search_chunks(
    *,
    query_vector: str | None,
    terms: list[str],
    limit: int = 8,
    source: str | None = None,
    category: str | None = None,
) -> list[dict]:
    """Hybrid retrieval: vector similarity fused with trigram term matching.

    `query_vector` is a pgvector literal (src.rag.embedding.to_literal) or None
    when the embedding provider is unavailable — in which case this degrades to
    the lexical channel alone rather than failing, which is the same
    fallback-rather-than-nothing choice ADR 0005 made for event grouping.

    Returns at most `limit` chunks, no more than MAX_CHUNKS_PER_ARTICLE from
    any one article, best first.
    """
    require_database_url()
    if not query_vector and not terms:
        return []

    params: dict = {"pool": CHANNEL_POOL, "k": RRF_K}
    channels: list[str] = []
    filters = ""
    if source:
        filters += " AND a.source = %(source)s"
        params["source"] = source
    if category:
        filters += " AND a.primary_category = %(category)s"
        params["category"] = category

    if query_vector:
        params["qv"] = query_vector
        channels.append(
            f"""
            semantic AS (
                SELECT c.chunk_id,
                       ROW_NUMBER() OVER (ORDER BY c.embedding <=> %(qv)s::vector) AS rank
                FROM article_chunks c
                JOIN articles a ON a.article_id = c.article_id
                WHERE c.embedding IS NOT NULL {filters}
                ORDER BY c.embedding <=> %(qv)s::vector
                LIMIT %(pool)s
            )"""
        )

    if terms:
        # One ILIKE per term, summed. Substring rather than word matching
        # because Hebrew fuses its prefixes onto the word (ה, ו, ב, ל, מ, כ, ש),
        # so "בכתבות" must match a search for "כתבות" — the same reasoning
        # src/db/browse.py records, now backed by a trigram index rather than a
        # sequential scan.
        for i, term in enumerate(terms):
            params[f"t{i}"] = f"%{term}%"
        matched = " + ".join(
            f"(CASE WHEN c.text ILIKE %(t{i})s THEN 1 ELSE 0 END)" for i in range(len(terms))
        )
        any_match = " OR ".join(f"c.text ILIKE %(t{i})s" for i in range(len(terms)))
        channels.append(
            f"""
            lexical AS (
                SELECT chunk_id,
                       ROW_NUMBER() OVER (
                           ORDER BY matched DESC, first_seen_at DESC, chunk_id
                       ) AS rank
                FROM (
                    SELECT c.chunk_id, a.first_seen_at, ({matched}) AS matched
                    FROM article_chunks c
                    JOIN articles a ON a.article_id = c.article_id
                    WHERE ({any_match}) {filters}
                ) m
                -- Recency breaks the tie, not chunk_id. Most questions match
                -- many chunks on one term, and among equally-matching chunks
                -- the newer coverage is the better answer; ordering on a hash
                -- made that draw arbitrary. chunk_id stays last so the order
                -- is still total and the result deterministic.
                ORDER BY matched DESC, first_seen_at DESC, chunk_id
                LIMIT %(pool)s
            )"""
        )

    if query_vector and terms:
        fused = f"""
            SELECT COALESCE(s.chunk_id, l.chunk_id) AS chunk_id,
                   COALESCE(1.0 / (%(k)s + s.rank), 0)
                 + COALESCE(1.0 / (%(k)s + l.rank), 0) AS score
            FROM semantic s
            FULL OUTER JOIN lexical l ON s.chunk_id = l.chunk_id
        """
    elif query_vector:
        fused = "SELECT chunk_id, 1.0 / (%(k)s + rank) AS score FROM semantic"
    else:
        fused = "SELECT chunk_id, 1.0 / (%(k)s + rank) AS score FROM lexical"

    # Over-fetch, because the per-article cap below discards rows. Without this
    # a single article filling the pool would leave the answer with two chunks.
    params["fetch"] = limit * MAX_CHUNKS_PER_ARTICLE + limit

    sql = f"""
        WITH {", ".join(channels)},
        fused AS ({fused})
        SELECT {_RESULT_COLUMNS}, f.score
        FROM fused f
        JOIN article_chunks c ON c.chunk_id = f.chunk_id
        {_RESULT_JOINS}
        ORDER BY f.score DESC, a.first_seen_at DESC, c.ordinal
        LIMIT %(fetch)s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]

    return _cap_per_article(rows, limit=limit)


def _cap_per_article(rows: list[dict], *, limit: int) -> list[dict]:
    """Keep the best MAX_CHUNKS_PER_ARTICLE chunks of each article, in order.

    In Python rather than a SQL window function so that the cap is readable and
    testable without a database — it is a policy about what an answer should
    look like, not a property of the index.
    """
    seen: dict[str, int] = {}
    kept: list[dict] = []
    for row in rows:
        article_id = row["article_id"]
        if seen.get(article_id, 0) >= MAX_CHUNKS_PER_ARTICLE:
            continue
        seen[article_id] = seen.get(article_id, 0) + 1
        kept.append(row)
        if len(kept) >= limit:
            break
    return kept

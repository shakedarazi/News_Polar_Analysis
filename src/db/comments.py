"""Comment persistence in PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.crawling.comments.models import RawComment
from src.db.config import require_database_url
from src.db.connection import get_connection


def make_comment_id(article_id: str, source_comment_id: str) -> str:
    return f"{article_id}:{source_comment_id}"


def iter_articles_for_comment_fetch(
    *,
    sources: list[str],
    min_age_hours: int = 24,
    missing_only: bool = True,
    limit: int | None = None,
) -> list[dict]:
    require_database_url()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)
    placeholders = ", ".join("%s" for _ in sources)
    query = f"""
        SELECT article_id, source, canonical_url, title, first_seen_at
        FROM articles
        WHERE source IN ({placeholders})
          AND first_seen_at <= %s
    """
    params: list = list(sources) + [cutoff]
    if missing_only:
        query += " AND comments_fetched_at IS NULL"
    query += " ORDER BY first_seen_at DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def save_comments(
    article_id: str,
    source: str,
    comments: list[RawComment],
    *,
    fetch_run_id: str,
) -> int:
    """Insert comments. Returns count of newly inserted rows."""
    require_database_url()
    now = datetime.now(timezone.utc)
    inserted = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for comment in comments:
                cid = make_comment_id(article_id, comment.source_comment_id)
                cur.execute(
                    """
                    INSERT INTO comments (
                        comment_id, article_id, source, text, author,
                        like_count, published_at, scraped_at, fetch_run_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (comment_id) DO NOTHING
                    RETURNING comment_id
                    """,
                    (
                        cid,
                        article_id,
                        source,
                        comment.text,
                        comment.author,
                        comment.like_count,
                        comment.published_at,
                        now,
                        fetch_run_id,
                    ),
                )
                if cur.fetchone():
                    inserted += 1

            cur.execute(
                """
                UPDATE articles SET comments_fetched_at = %s WHERE article_id = %s
                """,
                (now, article_id),
            )

    return inserted


def mark_unsupported_sources_fetched(*, min_age_hours: int = 24) -> int:
    """Mark articles from sources without comment APIs so they are not retried."""
    from src.crawling.comments.registry import UNSUPPORTED_SOURCES

    if not UNSUPPORTED_SOURCES:
        return 0
    require_database_url()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)
    placeholders = ", ".join("%s" for _ in UNSUPPORTED_SOURCES)
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE articles
                SET comments_fetched_at = %s
                WHERE source IN ({placeholders})
                  AND comments_fetched_at IS NULL
                  AND first_seen_at <= %s
                """,
                (now, *UNSUPPORTED_SOURCES, cutoff),
            )
            return cur.rowcount

    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM comments WHERE article_id = %s",
                (article_id,),
            )
            return int(cur.fetchone()[0])

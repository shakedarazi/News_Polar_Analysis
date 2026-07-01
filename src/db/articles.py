"""Article persistence in PostgreSQL."""

from __future__ import annotations

from datetime import datetime

from src.db.config import require_database_url
from src.db.connection import get_connection


def load_known_ids() -> set[str]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT article_id FROM articles")
            return {row[0] for row in cur.fetchall()}


def save_article(record: dict) -> bool:
    """
    Insert article if new. Returns True if inserted, False if duplicate.
    """
    require_database_url()

    first_seen = record["first_seen_at"]
    if isinstance(first_seen, str):
        first_seen = datetime.fromisoformat(first_seen)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO articles (
                    article_id, source, title, text,
                    canonical_url, first_seen_at, ingestion_run_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (article_id) DO NOTHING
                RETURNING article_id
                """,
                (
                    record["article_id"],
                    record["source"],
                    record.get("title"),
                    record["text"],
                    record["canonical_url"],
                    first_seen,
                    record["ingestion_run_id"],
                ),
            )
            return cur.fetchone() is not None

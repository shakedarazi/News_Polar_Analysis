"""Ingestion run observability persistence.

One row per (run_id, source) records how a single source's crawl went —
timestamps, per-article counts, and whether the source crashed outright —
so run history is queryable without grepping log files.
"""

from __future__ import annotations

from datetime import datetime

from src.db.config import require_database_url
from src.db.connection import get_connection


def record_ingestion_run(
    *,
    run_id: str,
    source: str,
    started_at: datetime,
    finished_at: datetime,
    saved: int = 0,
    skipped: int = 0,
    failed: int = 0,
    crashed: bool = False,
    error_message: str | None = None,
) -> None:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingestion_runs (
                    run_id, source, started_at, finished_at,
                    saved, skipped, failed, crashed, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, source) DO NOTHING
                """,
                (
                    run_id,
                    source,
                    started_at,
                    finished_at,
                    saved,
                    skipped,
                    failed,
                    crashed,
                    error_message,
                ),
            )

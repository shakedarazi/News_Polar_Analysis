"""Database schema migrations."""

from __future__ import annotations

from pathlib import Path

from src.db.connection import get_connection

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "sql" / "migrations"


def apply_migrations() -> None:
    if not _MIGRATIONS_DIR.is_dir():
        return
    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    with get_connection() as conn:
        with conn.cursor() as cur:
            for path in migration_files:
                cur.execute(path.read_text(encoding="utf-8"))

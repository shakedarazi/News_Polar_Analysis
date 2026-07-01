"""PostgreSQL connection helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from src.db.config import get_database_url


@contextmanager
def get_connection():
    import psycopg

    url = get_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    conn = psycopg.connect(url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(schema_path) -> None:
    from pathlib import Path

    sql = Path(schema_path).read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

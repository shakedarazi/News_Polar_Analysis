"""Export a local SQLite snapshot of the cloud Postgres (Neon) database.

Run once, with network, the day before the exhibition:

    PYTHONPATH=. python demo/snapshot/export_snapshot.py

The kiosk demo then runs entirely against demo/data/demo.sqlite — no cloud
dependency at showtime. Read-only against the main pipeline's DB; never
writes back.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.db.connection import get_connection  # noqa: E402

DATA_DIR = REPO_ROOT / "demo" / "data"
SQLITE_PATH = DATA_DIR / "demo.sqlite"

TABLES = {
    "articles": [
        "article_id", "source", "title", "text", "canonical_url",
        "first_seen_at", "primary_category", "category_confidence",
    ],
    "windows_features": [
        "article_id", "sentence_idx", "window_len",
        "c1", "c2", "c3", "c4", "c5", "c6", "c7",
        "active", "dominance", "lexicon_version",
    ],
    "comments": [
        "comment_id", "article_id", "source", "text", "like_count",
    ],
    "article_comments_agg": None,  # copy every column
}


def copy_table(pg_cur, lite: sqlite3.Connection, table: str, cols: list[str] | None) -> int:
    if cols is None:
        pg_cur.execute(
            "select column_name from information_schema.columns "
            "where table_name = %s order by ordinal_position",
            (table,),
        )
        cols = [r[0] for r in pg_cur.fetchall()]
    col_list = ", ".join(cols)
    lite.execute(f"drop table if exists {table}")
    lite.execute(f"create table {table} ({', '.join(c for c in cols)})")
    pg_cur.execute(f"select {col_list} from {table}")
    placeholders = ", ".join("?" for _ in cols)
    n = 0
    while True:
        rows = pg_cur.fetchmany(2000)
        if not rows:
            break
        lite.executemany(
            f"insert into {table} values ({placeholders})",
            [[str(v) if hasattr(v, "isoformat") else v for v in row] for row in rows],
        )
        n += len(rows)
    return n


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lite = sqlite3.connect(SQLITE_PATH)
    with get_connection() as conn, conn.cursor() as cur:
        for table, cols in TABLES.items():
            n = copy_table(cur, lite, table, cols)
            print(f"{table}: {n} rows")
    lite.execute("create index if not exists idx_wf_article on windows_features(article_id)")
    lite.execute("create index if not exists idx_c_article on comments(article_id)")
    lite.commit()
    lite.close()
    print(f"snapshot written to {SQLITE_PATH}")


if __name__ == "__main__":
    main()

"""Read-only access to the local demo snapshot (SQLite)."""

from __future__ import annotations

import sqlite3
from typing import Any

from demo import config


def connect() -> sqlite3.Connection:
    # check_same_thread=False: the connection is created during server startup
    # inside asyncio.to_thread but used afterwards only from the event loop —
    # single-threaded access, just not the creating thread.
    conn = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_article(conn: sqlite3.Connection, article_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "select * from articles where article_id = ?", (article_id,)
    ).fetchone()
    return dict(row) if row else None


def lexicon_counts(conn: sqlite3.Connection, article_id: str) -> list[int]:
    """Sum of per-window lexicon hits (c1..c7) for one article."""
    row = conn.execute(
        "select coalesce(sum(c1),0), coalesce(sum(c2),0), coalesce(sum(c3),0),"
        " coalesce(sum(c4),0), coalesce(sum(c5),0), coalesce(sum(c6),0),"
        " coalesce(sum(c7),0) from windows_features where article_id = ?",
        (article_id,),
    ).fetchone()
    return [int(v) for v in row]


def polarity_stats(conn: sqlite3.Connection, article_id: str) -> dict[str, Any]:
    row = conn.execute(
        "select count(*) as windows, avg(dominance) as mean_dominance,"
        " max(dominance) as max_dominance"
        " from windows_features where article_id = ? and dominance is not null",
        (article_id,),
    ).fetchone()
    agg = conn.execute(
        "select * from article_comments_agg where article_id = ?", (article_id,)
    ).fetchone()
    n_comments = conn.execute(
        "select count(*) from comments where article_id = ?", (article_id,)
    ).fetchone()[0]
    return {
        "windows": row["windows"],
        "mean_dominance": row["mean_dominance"],
        "max_dominance": row["max_dominance"],
        "comments": n_comments,
        "audience": dict(agg) if agg else None,
    }

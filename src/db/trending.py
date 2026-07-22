"""Trending-topics calculation for the "חם עכשיו" (Trending Now) dashboard widget.

A "topic" here is an article's existing `primary_category` (the same 9 fixed
categories used by TopicsCloud) — no new grouping concept is introduced.
Trending is entirely backend-aggregated SQL over real article timestamps;
nothing is computed by fetching all articles into the browser, and nothing
is hardcoded.

Formula (deterministic, mirrors the rest of the analysis layer):
  - current_count   = articles in that category first_seen within the last
                       CURRENT_WINDOW_HOURS hours (from NOW()).
  - previous_count   = articles in that category first_seen in the
                       COMPARISON_WINDOW_HOURS-hour window immediately before
                       the current window.
  - growth_pct       = (current_count - previous_count) / previous_count * 100,
                       or None when previous_count == 0 (see `direction` below
                       instead of a division by zero / infinite percentage).
  - direction        = "new"  when previous_count == 0 and current_count > 0
                       "up"   when growth_pct >= UP_THRESHOLD_PCT
                       "down" when growth_pct <= DOWN_THRESHOLD_PCT
                       "flat" otherwise
  - unique_sources   = distinct sources publishing in that category in the
                       current window (cross-source coverage signal).
  - score            = current_count * growth_boost * source_boost, where
                       growth_boost = 2.0 if direction == "new" else
                                      1.0 + max(0.0, min(growth_pct, 200.0)) / 100.0
                       source_boost = 1.0 + 0.1 * (unique_sources - 1)
                       — a topic that is both growing and covered by more than
                       one source ranks above one with raw volume alone.

Only categories with current_count > 0 are eligible; the top `limit` by score
are returned, ranked 1..limit.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.db.config import require_database_url
from src.db.connection import get_connection

CURRENT_WINDOW_HOURS = 24
COMPARISON_WINDOW_HOURS = 24
SPARKLINE_DAYS = 7
DEFAULT_LIMIT = 6
UP_THRESHOLD_PCT = 5.0
DOWN_THRESHOLD_PCT = -5.0


def _direction(previous_count: int, growth_pct: float | None) -> str:
    if previous_count == 0:
        return "new"
    if growth_pct is None:
        return "flat"
    if growth_pct >= UP_THRESHOLD_PCT:
        return "up"
    if growth_pct <= DOWN_THRESHOLD_PCT:
        return "down"
    return "flat"


def _score(current_count: int, previous_count: int, growth_pct: float | None, unique_sources: int) -> float:
    if previous_count == 0:
        growth_boost = 2.0
    else:
        growth_boost = 1.0 + max(0.0, min(growth_pct or 0.0, 200.0)) / 100.0
    source_boost = 1.0 + 0.1 * max(0, unique_sources - 1)
    return current_count * growth_boost * source_boost


def get_trending_topics(limit: int = DEFAULT_LIMIT) -> list[dict]:
    require_database_url()
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(hours=CURRENT_WINDOW_HOURS)
    previous_start = current_start - timedelta(hours=COMPARISON_WINDOW_HOURS)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    primary_category,
                    COUNT(*) FILTER (WHERE first_seen_at >= %(current_start)s) AS current_count,
                    COUNT(*) FILTER (
                        WHERE first_seen_at >= %(previous_start)s
                          AND first_seen_at < %(current_start)s
                    ) AS previous_count,
                    COUNT(DISTINCT source) FILTER (
                        WHERE first_seen_at >= %(current_start)s
                    ) AS unique_sources
                FROM articles
                WHERE primary_category IS NOT NULL
                  AND first_seen_at >= %(previous_start)s
                GROUP BY primary_category
                """,
                {"current_start": current_start, "previous_start": previous_start},
            )
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]

            topics = []
            for row in rows:
                current_count = row["current_count"]
                previous_count = row["previous_count"]
                if current_count <= 0:
                    continue
                growth_pct = (
                    (current_count - previous_count) / previous_count * 100.0
                    if previous_count > 0
                    else None
                )
                topics.append(
                    {
                        "topic": row["primary_category"],
                        "current_count": current_count,
                        "previous_count": previous_count,
                        "unique_sources": row["unique_sources"],
                        "growth_pct": growth_pct,
                        "direction": _direction(previous_count, growth_pct),
                        "_score": _score(current_count, previous_count, growth_pct, row["unique_sources"]),
                    }
                )

            topics.sort(key=lambda t: t["_score"], reverse=True)
            top = topics[:limit]
            top_names = [t["topic"] for t in top]

            sparkline_by_topic: dict[str, list[dict]] = {name: [] for name in top_names}
            if top_names:
                sparkline_start = now - timedelta(days=SPARKLINE_DAYS)
                cur.execute(
                    """
                    SELECT primary_category, first_seen_at::date AS day, COUNT(*) AS cnt
                    FROM articles
                    WHERE primary_category = ANY(%s)
                      AND first_seen_at >= %s
                    GROUP BY primary_category, day
                    ORDER BY day
                    """,
                    (top_names, sparkline_start),
                )
                spark_cols = [d[0] for d in cur.description]
                for r in cur.fetchall():
                    rec = dict(zip(spark_cols, r))
                    sparkline_by_topic[rec["primary_category"]].append(
                        {"date": rec["day"].isoformat(), "count": rec["cnt"]}
                    )

            for rank, t in enumerate(top, start=1):
                t["rank"] = rank
                t["sparkline"] = sparkline_by_topic.get(t["topic"], [])
                del t["_score"]

            return top

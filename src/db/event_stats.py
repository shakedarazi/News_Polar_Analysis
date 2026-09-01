"""Reads backing the within-event outlet profile (src/analysis/event_stats.py).

The rule this module exists to enforce is egress, not correctness: the event
grouping already carries every article_id it clustered, so the metric values
for a whole profile are fetched in ONE query over those ids. Going back through
get_event_detail() per event is what once made an endpoint take ~24 seconds.
"""

from __future__ import annotations

from src.analysis.event_grouping import get_events
from src.analysis.event_stats import METRICS, Version, source_profiles
from src.db.config import require_database_url
from src.db.connection import get_connection

# How many events to profile. The grouping pass is cached, and the metric query
# is a single ANY() over the union of their article ids, so this bound is about
# how much corpus a claim rests on rather than about query cost.
DEFAULT_EVENT_LIMIT = 400

# Column expressions per metric. `dominance` is the article's mean window
# dominance; windows with no lexicon word store NULL and AVG skips them, which
# is the same treatment the article page's chart gives them.
_METRIC_SQL = {
    "dominance": "win.mean_dominance",
    "audience_mean": "agg.audience_mean",
    "audience_p85": "agg.audience_p85",
    "audience_issue_mean": "agg.audience_issue_mean",
    "audience_affective_mean": "agg.audience_affective_mean",
}


def _fetch_metric_rows(article_ids: list[str], metric: str) -> dict[str, dict]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    a.article_id,
                    a.source,
                    {_METRIC_SQL[metric]} AS value,
                    COALESCE(agg.num_comments, 0) AS num_comments
                FROM articles a
                LEFT JOIN LATERAL (
                    SELECT num_comments, audience_mean, audience_p85,
                           audience_issue_mean, audience_affective_mean
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                LEFT JOIN LATERAL (
                    SELECT AVG(dominance) AS mean_dominance
                    FROM windows_features
                    WHERE article_id = a.article_id
                ) win ON TRUE
                WHERE a.article_id = ANY(%s)
                """,
                (article_ids,),
            )
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    return {r["article_id"]: r for r in rows}


def get_source_profiles(
    *,
    metric: str = "audience_mean",
    category: str | None = None,
    event_limit: int = DEFAULT_EVENT_LIMIT,
) -> dict:
    """Per-outlet deviation from the event median, over recent events.

    Articles whose metric is NULL are dropped before the median is taken, so an
    outlet that has no audience data for a story simply does not vote on that
    story's median — it is never counted as a zero.
    """
    if metric not in METRICS:
        raise ValueError(f"Unknown metric: {metric}")

    events = get_events(category=category, limit=event_limit)
    multi_source = [e for e in events if e["source_count"] >= 2]
    all_ids = sorted({aid for e in multi_source for aid in e["article_ids"]})
    if not all_ids:
        return {
            "metric": metric,
            "sources": [],
            "events_used": 0,
            "pair_events": 0,
            "pair_share": None,
            "tests_run": 0,
            "min_observations": 0,
            "events_considered": len(multi_source),
        }

    by_article = _fetch_metric_rows(all_ids, metric)

    versions_by_event: dict[str, list[Version]] = {}
    for event in multi_source:
        versions = []
        for article_id in event["article_ids"]:
            row = by_article.get(article_id)
            if row is None or row["value"] is None:
                continue
            versions.append(
                Version(
                    article_id=article_id,
                    source=row["source"],
                    value=float(row["value"]),
                    weight=int(row["num_comments"] or 0),
                )
            )
        if versions:
            versions_by_event[event["event_id"]] = versions

    profile = source_profiles(versions_by_event)
    profile["metric"] = metric
    profile["events_considered"] = len(multi_source)
    return profile


def get_event_deviation(event_id: str, *, metric: str = "audience_mean") -> dict | None:
    """The same construction for a single event: each outlet's version, the
    event median, and the distance between them.

    This is the shape the event page shows, and it is the unit the aggregate
    profile is built from — a reader who distrusts the aggregate can open one
    event and see the whole arithmetic.
    """
    if metric not in METRICS:
        raise ValueError(f"Unknown metric: {metric}")

    from src.analysis.event_grouping import get_event_article_ids
    from src.analysis.event_stats import median, one_per_source

    article_ids = get_event_article_ids(event_id)
    if not article_ids:
        return None

    by_article = _fetch_metric_rows(article_ids, metric)
    versions = [
        Version(
            article_id=aid,
            source=row["source"],
            value=float(row["value"]),
            weight=int(row["num_comments"] or 0),
        )
        for aid in article_ids
        if (row := by_article.get(aid)) is not None and row["value"] is not None
    ]
    counted = one_per_source(versions)
    if len(counted) < 2:
        return {
            "event_id": event_id,
            "metric": metric,
            "median": None,
            "versions": [],
            "comparable": False,
        }

    event_median = median([v.value for v in counted])
    return {
        "event_id": event_id,
        "metric": metric,
        "median": event_median,
        "comparable": True,
        "versions": [
            {
                "article_id": v.article_id,
                "source": v.source,
                "value": v.value,
                "deviation": v.value - event_median,
                "num_comments": v.weight,
            }
            for v in sorted(counted, key=lambda v: v.value, reverse=True)
        ],
    }

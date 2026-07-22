"""Read-only queries for the event timeline.

Event detection itself lives in src/analysis/event_grouping.py (deterministic
grouping over category + time proximity + title overlap — see that module
for why no persistent event/cluster id was needed). This module joins in the
per-article display fields already computed elsewhere in the system:
audience polarity (article_comments_agg), AI summary sentiment
(articles.summary_sentiment), and political bias (articles.bias_*) — never
recomputing or approximating any of them.
"""

from __future__ import annotations

from src.analysis.event_grouping import get_event_article_ids, get_events
from src.db.config import require_database_url
from src.db.connection import get_connection

STILL_DEVELOPING_HOURS = 24


def _fetch_article_rows(article_ids: list[str]) -> list[dict]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.article_id, a.source, a.title, a.canonical_url,
                    a.primary_category, a.first_seen_at,
                    a.summary_sentiment, a.bias_label, a.bias_score,
                    a.bias_confidence,
                    LEFT(a.text, 200) AS snippet,
                    agg.audience_mean
                FROM articles a
                LEFT JOIN LATERAL (
                    SELECT audience_mean
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                WHERE a.article_id = ANY(%s)
                ORDER BY a.first_seen_at
                """,
                (article_ids,),
            )
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]


def _status_labels(rows: list[dict]) -> list[str]:
    labels: list[str] = []
    seen_sources: set[str] = set()
    prev_sentiment: str | None = None
    for i, row in enumerate(rows):
        if i == 0:
            labels.append("פרסום ראשון")
        elif row["source"] not in seen_sources:
            labels.append("מקור נוסף הצטרף לסיקור")
        elif row["summary_sentiment"] and row["summary_sentiment"] != prev_sentiment:
            labels.append("שינוי בסנטימנט")
        else:
            labels.append("עדכון חדש")
        seen_sources.add(row["source"])
        if row["summary_sentiment"]:
            prev_sentiment = row["summary_sentiment"]
    return labels


def _dominant_sentiment(rows: list[dict]) -> str | None:
    counts: dict[str, int] = {}
    for row in rows:
        sentiment = row["summary_sentiment"]
        if sentiment:
            counts[sentiment] = counts.get(sentiment, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _bias_distribution(rows: list[dict]) -> dict[str, int] | None:
    counts: dict[str, int] = {}
    for row in rows:
        label = row["bias_label"]
        if label:
            counts[label] = counts.get(label, 0) + 1
    return counts or None


def list_events(
    *,
    category: str | None = None,
    source: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 20,
) -> list[dict]:
    # Over-fetch before filtering by source/date, since those aren't part of
    # the grouping query itself (kept there deliberately simple/reusable).
    events = get_events(category=category, limit=max(limit * 4, 40))

    if source:
        events = [e for e in events if source in e["sources"]]
    if start_date:
        events = [e for e in events if e["first_seen_at"].date().isoformat() >= start_date]
    if end_date:
        events = [e for e in events if e["first_seen_at"].date().isoformat() <= end_date]

    return events[:limit]


def get_event_detail(event_id: str) -> dict | None:
    article_ids = get_event_article_ids(event_id)
    if not article_ids:
        return None
    rows = _fetch_article_rows(article_ids)
    if not rows:
        return None

    labels = _status_labels(rows)
    audience_values = [r["audience_mean"] for r in rows if r["audience_mean"] is not None]

    return {
        "event_id": event_id,
        "title": max((r["title"] for r in rows if r["title"]), key=len, default=None),
        "primary_category": rows[0]["primary_category"],
        "article_count": len(rows),
        "source_count": len({r["source"] for r in rows}),
        "first_seen_at": rows[0]["first_seen_at"],
        "last_seen_at": rows[-1]["first_seen_at"],
        "dominant_sentiment": _dominant_sentiment(rows),
        "bias_distribution": _bias_distribution(rows),
        "avg_audience_mean": (
            sum(audience_values) / len(audience_values) if audience_values else None
        ),
        "timeline": [{**row, "status_label": label} for row, label in zip(rows, labels)],
    }

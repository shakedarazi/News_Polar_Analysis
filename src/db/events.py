"""Read-only queries for the event timeline.

Event detection itself lives in src/analysis/event_grouping.py: articles are
grouped by embedding similarity during ingestion and carry the resulting
`articles.event_id`, with the older title-overlap grouping kept only as a
fallback for a corpus no embedding pass has reached (docs/adr/0005). Which of
the two is in force is decided per corpus, so this module never has to ask.
It joins in the per-article display fields already computed elsewhere in the
system: audience polarity (article_comments_agg), AI summary sentiment
(articles.summary_sentiment), and political bias (articles.bias_*) — never
recomputing or approximating any of them.
"""

from __future__ import annotations

from src.analysis.event_grouping import (
    find_event_for_article,
    get_event_article_ids,
    get_events,
)
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


def _count_bias_labels(
    ids_by_event: dict[str, list[str]], label_by_article: dict[str, str]
) -> dict[str, dict[str, int]]:
    """Tally bias labels per event. Events with no labelled article are
    omitted entirely, matching get_event_detail()'s `bias_distribution: None`."""
    distributions: dict[str, dict[str, int]] = {}
    for event_id, article_ids in ids_by_event.items():
        counts: dict[str, int] = {}
        for article_id in article_ids:
            label = label_by_article.get(article_id)
            if label:
                counts[label] = counts.get(label, 0) + 1
        if counts:
            distributions[event_id] = counts
    return distributions


def get_events_bias_distributions(events: list[dict]) -> dict[str, dict[str, int]]:
    """Bias-label counts for many events, in a single query.

    Events from get_events() already carry their own `article_ids`, so a
    caller that only needs the bias mix must not go back through
    get_event_detail(): that re-runs the whole clustering pass per event
    (get_event_article_ids) and then fetches the full timeline payload. Doing
    that once per event is what made GET /api/alerts take ~24s.
    """
    ids_by_event = {e["event_id"]: e["article_ids"] for e in events}
    all_ids = sorted({aid for ids in ids_by_event.values() for aid in ids})
    if not all_ids:
        return {}

    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT article_id, bias_label
                FROM articles
                WHERE article_id = ANY(%s) AND bias_label IS NOT NULL
                """,
                (all_ids,),
            )
            label_by_article = {row[0]: row[1] for row in cur.fetchall()}

    return _count_bias_labels(ids_by_event, label_by_article)


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


def get_article_event(article_id: str) -> dict | None:
    """The event one article belongs to, as the little the article page needs
    to link back to it — or None when the article stands alone.

    Only the fields already in the cached grouping are returned, so this adds
    no query to the article detail request.
    """
    event = find_event_for_article(article_id)
    if event is None:
        return None
    return {
        "event_id": event["event_id"],
        "title": event["title"],
        "article_count": event["article_count"],
        "source_count": event["source_count"],
    }


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

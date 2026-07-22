"""Smart alert detection — deterministic, threshold-based, over real data only.

Every threshold is defined once, here, instead of being scattered as magic
numbers across the codebase. Each detector returns candidate alerts as plain
dicts; src/db/alerts.py is responsible for persisting them (with a dedup_key
that makes re-running detection a no-op for a condition that already fired).

No alert type here is randomly generated or fabricated — each one queries
real article/event/bias data already computed elsewhere in the system
(src/db/trending.py, src/analysis/event_grouping.py, articles.bias_*,
article_comments_agg). "Article processing failure" alerts (mentioned as a
possible type in the spec, gated on "authorized users when roles exist") are
intentionally not implemented: this system has no user/role model at all, so
that precondition is never met — see docs/README or CLAUDE.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.analysis.event_grouping import get_events
from src.db.config import require_database_url
from src.db.connection import get_connection
from src.db.trending import CURRENT_WINDOW_HOURS, COMPARISON_WINDOW_HOURS, get_trending_topics

# A topic's current-24h volume must grow by at least this much over the
# previous 24h window, AND have at least MIN_ARTICLES articles now, to count
# as a real spike (guards against e.g. 1 -> 2 articles reading as "+100%").
TOPIC_SPIKE_MIN_GROWTH_PCT = 50.0
TOPIC_SPIKE_MIN_ARTICLES = 3

# A source publishing at least this many articles in the current 24h window,
# and at least doubling its previous-24h volume, counts as unusual activity.
SOURCE_ACTIVITY_MIN_ARTICLES = 8
SOURCE_ACTIVITY_MIN_GROWTH_PCT = 100.0

# Minimum |change| in a topic's average audience polarity between the
# current and previous 24h window to count as a real shift. Matches the
# mid-polarity band width used elsewhere (frontend/src/lib/format.ts
# polarLevel(): low/mid boundary is 0.05), so "shift" means "crossed a band".
SENTIMENT_SHIFT_MIN_DELTA = 0.05
SENTIMENT_SHIFT_MIN_ARTICLES = 3  # per window, so the average isn't 1-2 comments' noise

# An event needs coverage with at least this many distinct bias labels
# (each backed by >=1 article whose bias was actually generated) to be
# flagged as "polarized coverage of the same event".
POLARIZATION_MIN_DISTINCT_LABELS = 2

# An event must already have this many distinct sources to be worth
# surfacing as a "new developing event" alert (matches the same bar
# event_grouping uses to consider something an event at all: >=2 members,
# but sources specifically, not just article count).
DEVELOPING_EVENT_MIN_SOURCES = 2
STILL_DEVELOPING_HOURS = 24


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def detect_topic_spikes() -> list[dict]:
    """Despite the name (kept for dedup_key/alert_type stability), this now
    covers both trending event and trending entity/phrase items — see
    src/db/trending.py, which no longer groups by generic category."""
    candidates = []
    for item in get_trending_topics(limit=12):
        if item["current_count"] < TOPIC_SPIKE_MIN_ARTICLES:
            continue
        is_spike = item["direction"] == "new" or (
            item["growth_pct"] is not None and item["growth_pct"] >= TOPIC_SPIKE_MIN_GROWTH_PCT
        )
        if not is_spike:
            continue
        growth_label = (
            "כתבות חדשות (ללא נתונים בתקופה הקודמת)"
            if item["growth_pct"] is None
            else f"עלייה של {item['growth_pct']:.0f}%"
        )
        candidates.append(
            {
                "alert_type": "topic_spike",
                "severity": "medium",
                "title": f'עלייה חדה ב"{item["name"]}"',
                "message": (
                    f'{item["current_count"]} כתבות הקשורות ל"{item["name"]}" ב-{CURRENT_WINDOW_HOURS} '
                    f"השעות האחרונות ({growth_label}), מ-{item['unique_sources']} מקורות."
                ),
                "related_topic": item["name"],
                "related_source": None,
                "related_article_id": None,
                "related_event_id": item["event_id"],
                "link_path": item["href"],
                "dedup_key": f"topic_spike:{item['item_type']}:{item['name']}:{_today_key()}",
            }
        )
    return candidates


def detect_source_activity() -> list[dict]:
    require_database_url()
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(hours=CURRENT_WINDOW_HOURS)
    previous_start = current_start - timedelta(hours=COMPARISON_WINDOW_HOURS)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    source,
                    COUNT(*) FILTER (WHERE first_seen_at >= %(current_start)s) AS current_count,
                    COUNT(*) FILTER (
                        WHERE first_seen_at >= %(previous_start)s AND first_seen_at < %(current_start)s
                    ) AS previous_count
                FROM articles
                WHERE first_seen_at >= %(previous_start)s
                GROUP BY source
                """,
                {"current_start": current_start, "previous_start": previous_start},
            )
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]

    candidates = []
    for row in rows:
        current_count = row["current_count"]
        previous_count = row["previous_count"]
        if current_count < SOURCE_ACTIVITY_MIN_ARTICLES:
            continue
        growth_pct = (
            (current_count - previous_count) / previous_count * 100.0 if previous_count > 0 else None
        )
        is_unusual = growth_pct is None or growth_pct >= SOURCE_ACTIVITY_MIN_GROWTH_PCT
        if not is_unusual:
            continue
        candidates.append(
            {
                "alert_type": "source_activity",
                "severity": "low",
                "title": f'פעילות פרסום חריגה במקור "{row["source"]}"',
                "message": (
                    f'{current_count} כתבות פורסמו על ידי {row["source"]} ב-{CURRENT_WINDOW_HOURS} '
                    f"השעות האחרונות, לעומת {previous_count} בתקופה המקבילה הקודמת."
                ),
                "related_topic": None,
                "related_source": row["source"],
                "related_article_id": None,
                "related_event_id": None,
                "link_path": f"/articles?source={row['source']}",
                "dedup_key": f"source_activity:{row['source']}:{_today_key()}",
            }
        )
    return candidates


def detect_sentiment_shifts() -> list[dict]:
    require_database_url()
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(hours=CURRENT_WINDOW_HOURS)
    previous_start = current_start - timedelta(hours=COMPARISON_WINDOW_HOURS)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.primary_category,
                    AVG(agg.audience_mean) FILTER (WHERE a.first_seen_at >= %(current_start)s) AS current_avg,
                    COUNT(*) FILTER (WHERE a.first_seen_at >= %(current_start)s) AS current_n,
                    AVG(agg.audience_mean) FILTER (
                        WHERE a.first_seen_at >= %(previous_start)s AND a.first_seen_at < %(current_start)s
                    ) AS previous_avg,
                    COUNT(*) FILTER (
                        WHERE a.first_seen_at >= %(previous_start)s AND a.first_seen_at < %(current_start)s
                    ) AS previous_n
                FROM articles a
                JOIN LATERAL (
                    SELECT audience_mean
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                WHERE a.primary_category IS NOT NULL
                  AND a.first_seen_at >= %(previous_start)s
                GROUP BY a.primary_category
                """,
                {"current_start": current_start, "previous_start": previous_start},
            )
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]

    candidates = []
    for row in rows:
        if (
            row["current_avg"] is None
            or row["previous_avg"] is None
            or row["current_n"] < SENTIMENT_SHIFT_MIN_ARTICLES
            or row["previous_n"] < SENTIMENT_SHIFT_MIN_ARTICLES
        ):
            continue
        delta = float(row["current_avg"]) - float(row["previous_avg"])
        if abs(delta) < SENTIMENT_SHIFT_MIN_DELTA:
            continue
        direction = "עלייה" if delta > 0 else "ירידה"
        candidates.append(
            {
                "alert_type": "sentiment_shift",
                "severity": "medium",
                "title": f'שינוי בקיטוב הקהל בנושא "{row["primary_category"]}"',
                "message": (
                    f'{direction} של {abs(delta) * 100:.1f} נקודות אחוז בקיטוב הממוצע בתגובות על כתבות '
                    f'בנושא "{row["primary_category"]}", לעומת התקופה המקבילה הקודמת.'
                ),
                "related_topic": row["primary_category"],
                "related_source": None,
                "related_article_id": None,
                "related_event_id": None,
                "link_path": f"/?category={row['primary_category']}#trend",
                "dedup_key": f"sentiment_shift:{row['primary_category']}:{_today_key()}",
            }
        )
    return candidates


def detect_event_polarization() -> list[dict]:
    from src.db.events import get_event_detail

    candidates = []
    for event in get_events(limit=30):
        if event["source_count"] < POLARIZATION_MIN_DISTINCT_LABELS:
            continue
        detail = get_event_detail(event["event_id"])
        if not detail or not detail["bias_distribution"]:
            continue
        distinct_labels = [label for label, count in detail["bias_distribution"].items() if count > 0]
        if len(distinct_labels) < POLARIZATION_MIN_DISTINCT_LABELS:
            continue
        labels_str = ", ".join(distinct_labels)
        candidates.append(
            {
                "alert_type": "event_polarization",
                "severity": "high",
                "title": "מחלוקת בסיקור פוליטי של אותו אירוע",
                "message": (
                    f'הכתבות המסקרות את האירוע "{event["title"]}" מציגות נטיות פוליטיות שונות '
                    f"({labels_str}) בין המקורות."
                ),
                "related_topic": None,
                "related_source": None,
                "related_article_id": None,
                "related_event_id": event["event_id"],
                "link_path": f"/events/{event['event_id']}",
                "dedup_key": f"event_polarization:{event['event_id']}",
            }
        )
    return candidates


def detect_new_developing_events() -> list[dict]:
    now = datetime.now(timezone.utc)
    candidates = []
    for event in get_events(limit=30):
        if event["source_count"] < DEVELOPING_EVENT_MIN_SOURCES:
            continue
        age_hours = (now - event["last_seen_at"]).total_seconds() / 3600.0
        if age_hours > STILL_DEVELOPING_HOURS:
            continue
        candidates.append(
            {
                "alert_type": "new_event",
                "severity": "medium",
                "title": "אירוע חדש מתפתח",
                "message": (
                    f'"{event["title"]}" — {event["article_count"]} כתבות מ-{event["source_count"]} '
                    "מקורות עד כה, והסיקור עדיין נמשך."
                ),
                "related_topic": None,
                "related_source": None,
                "related_article_id": None,
                "related_event_id": event["event_id"],
                "link_path": f"/events/{event['event_id']}",
                "dedup_key": f"new_event:{event['event_id']}",
            }
        )
    return candidates


def detect_all_alerts() -> list[dict]:
    return [
        *detect_topic_spikes(),
        *detect_source_activity(),
        *detect_sentiment_shifts(),
        *detect_event_polarization(),
        *detect_new_developing_events(),
    ]

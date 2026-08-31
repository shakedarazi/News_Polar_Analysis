"""Trending-now calculation for the "חם עכשיו" dashboard widget.

Surfaces real, specific things — events and entities/phrases actually
mentioned in article titles — never the 9 generic AI categories
(primary_category). Two signal sources, merged into one ranked list:

  1. Detected events (src.analysis.event_grouping) — already-clustered
     multi-article stories with a real descriptive title (e.g. "בארי לויט
     בן ה-80 נהרג באסון קריסת המרפסת בירושלים"). These link to their own
     /events/{id} timeline page.
  2. Salient keyword/entity phrases — 1-2 word n-grams extracted from
     titles (see src.analysis.text_keywords) — that recur across
     MIN_ENTITY_ARTICLES+ distinct articles from MIN_ENTITY_SOURCES+
     distinct sources in the current window. This is what catches a
     persistent entity like "איראן" or "נתניהו" that isn't necessarily one
     clustered story. These link to a filtered article search
     (/articles?q=<phrase>).

Both share the same current/previous-window growth+recency scoring formula
(see _score()) — entirely backend-aggregated, nothing computed by fetching
all articles into the browser, and nothing hardcoded.

Formula (deterministic, mirrors the rest of the analysis layer):
  - current_count   = distinct articles for that item first_seen within the
                       last CURRENT_WINDOW_HOURS hours (from NOW()).
  - previous_count   = same, in the COMPARISON_WINDOW_HOURS-hour window
                       immediately before the current window.
  - growth_pct       = (current_count - previous_count) / previous_count * 100,
                       or None when previous_count == 0 (see `direction`
                       below instead of a division by zero / infinite %).
  - direction        = "new"  when previous_count == 0 and current_count > 0
                       "up"   when growth_pct >= UP_THRESHOLD_PCT
                       "down" when growth_pct <= DOWN_THRESHOLD_PCT
                       "flat" otherwise
  - unique_sources   = distinct sources covering it in the current window.
  - score            = current_count * growth_boost * source_boost, where
                       growth_boost = 2.0 if direction == "new" else
                                      1.0 + max(0.0, min(growth_pct, 200.0)) / 100.0
                       source_boost = 1.0 + 0.1 * (unique_sources - 1)

To avoid showing the same story twice (e.g. both a "קריסת המרפסת" event and
a "לויט" entity pointing at the same 3 articles), an entity is dropped if
more than ENTITY_EVENT_OVERLAP_MAX of its current-window articles are
already covered by a higher-ranked, already-selected event. Among entity
candidates whose current-window article set is identical, only the longest
phrase is kept (e.g. "בנימין נתניהו" over "נתניהו").
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from src.analysis.event_grouping import get_events
from src.analysis.text_keywords import extract_ngrams
from src.db.config import require_database_url
from src.db.connection import get_connection

CURRENT_WINDOW_HOURS = 24
COMPARISON_WINDOW_HOURS = 24
SPARKLINE_DAYS = 7
DEFAULT_LIMIT = 6
UP_THRESHOLD_PCT = 5.0
DOWN_THRESHOLD_PCT = -5.0

MIN_ENTITY_ARTICLES = 3
MIN_ENTITY_SOURCES = 2
ENTITY_EVENT_OVERLAP_MAX = 0.6


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


def _fetch_window_articles(previous_start: datetime) -> list[dict]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT article_id, title, source, first_seen_at
                FROM articles
                WHERE first_seen_at >= %s
                """,
                (previous_start,),
            )
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]


def _event_candidates(current_start: datetime, events: list[dict] | None = None) -> list[dict]:
    candidates = []
    for event in get_events(limit=100) if events is None else events:
        members = event["members"]
        current_ids = {m["article_id"] for m in members if m["first_seen_at"] >= current_start}
        if not current_ids:
            continue
        previous_ids = {m["article_id"] for m in members if m["first_seen_at"] < current_start}
        current_sources = {m["source"] for m in members if m["article_id"] in current_ids}
        candidates.append(
            {
                "item_type": "event",
                "name": event["title"],
                "event_id": event["event_id"],
                "current_count": len(current_ids),
                "previous_count": len(previous_ids),
                "unique_sources": len(current_sources),
                "_current_article_ids": current_ids,
                "_day_counts": _bucket_by_day(members),
            }
        )
    return candidates


def _bucket_by_day(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["first_seen_at"].date().isoformat()] += 1
    return counts


# Single-letter Hebrew prepositions/conjunctions that attach directly to the
# following word with no separator (ב-, ל-, מ-, ו-, כ-, ש-, ה-), e.g.
# "איראן" / "באיראן" / "לאיראן" are the same real-world entity. Merged only
# when BOTH the prefixed and bare forms already independently appear as
# candidate phrases — never by blindly stripping an assumed prefix, which
# would corrupt a real name that happens to start with one of these letters
# (e.g. "בנימין" is not the preposition ב + "נימין").
_HEBREW_PREFIX_LETTERS = "בלמוכשה"


def _merge_prefix_variants(
    phrase_current_ids: dict[str, set[str]],
    phrase_previous_ids: dict[str, set[str]],
    phrase_sources_current: dict[str, set[str]],
    phrase_day_rows: dict[str, list[dict]],
) -> None:
    for phrase in list(phrase_current_ids.keys()):
        if len(phrase) < 3 or phrase[0] not in _HEBREW_PREFIX_LETTERS:
            continue
        base = phrase[1:]
        if base not in phrase_current_ids or base == phrase:
            continue
        phrase_current_ids[base] |= phrase_current_ids.pop(phrase)
        phrase_previous_ids[base] |= phrase_previous_ids.pop(phrase, set())
        phrase_sources_current[base] |= phrase_sources_current.pop(phrase, set())
        phrase_day_rows[base].extend(phrase_day_rows.pop(phrase, []))


def _entity_candidates(articles: list[dict], current_start: datetime) -> list[dict]:
    phrase_current_ids: dict[str, set[str]] = defaultdict(set)
    phrase_previous_ids: dict[str, set[str]] = defaultdict(set)
    phrase_sources_current: dict[str, set[str]] = defaultdict(set)
    phrase_day_rows: dict[str, list[dict]] = defaultdict(list)

    for a in articles:
        grams = set(extract_ngrams(a["title"], max_n=2))
        is_current = a["first_seen_at"] >= current_start
        for g in grams:
            phrase_day_rows[g].append(a)
            if is_current:
                phrase_current_ids[g].add(a["article_id"])
                phrase_sources_current[g].add(a["source"])
            else:
                phrase_previous_ids[g].add(a["article_id"])

    _merge_prefix_variants(
        phrase_current_ids, phrase_previous_ids, phrase_sources_current, phrase_day_rows
    )

    candidates = []
    for phrase, current_ids in phrase_current_ids.items():
        if len(current_ids) < MIN_ENTITY_ARTICLES:
            continue
        sources = phrase_sources_current[phrase]
        if len(sources) < MIN_ENTITY_SOURCES:
            continue
        candidates.append(
            {
                "item_type": "entity",
                "name": phrase,
                "event_id": None,
                "current_count": len(current_ids),
                "previous_count": len(phrase_previous_ids.get(phrase, set())),
                "unique_sources": len(sources),
                "_current_article_ids": current_ids,
                "_day_counts": _bucket_by_day(phrase_day_rows[phrase]),
            }
        )
    return _dedup_subsumed_entities(candidates)


def _dedup_subsumed_entities(candidates: list[dict]) -> list[dict]:
    """When two phrases cover the exact same current-window articles (e.g.
    "נתניהו" and "בנימین נתניהו" always appear together), keep only the
    longer, more specific phrase."""
    best_by_articleset: dict[frozenset, dict] = {}
    for c in candidates:
        key = frozenset(c["_current_article_ids"])
        existing = best_by_articleset.get(key)
        if existing is None or len(c["name"].split()) > len(existing["name"].split()):
            best_by_articleset[key] = c
    return list(best_by_articleset.values())


def _finalize(item: dict, rank: int, now: datetime) -> dict:
    sparkline_start = (now - timedelta(days=SPARKLINE_DAYS)).date()
    sparkline = sorted(
        (
            {"date": day, "count": count}
            for day, count in item["_day_counts"].items()
            if day >= sparkline_start.isoformat()
        ),
        key=lambda p: p["date"],
    )
    return {
        "rank": rank,
        "item_type": item["item_type"],
        "name": item["name"],
        "event_id": item["event_id"],
        "current_count": item["current_count"],
        "previous_count": item["previous_count"],
        "unique_sources": item["unique_sources"],
        "growth_pct": item["growth_pct"],
        "direction": item["direction"],
        "sparkline": sparkline,
        "href": (
            f"/events/{item['event_id']}"
            if item["item_type"] == "event"
            else f"/articles?q={quote(item['name'])}"
        ),
    }


def get_trending_topics(limit: int = DEFAULT_LIMIT, *, events: list[dict] | None = None) -> list[dict]:
    """`events` lets a caller that already ran get_events() hand the result in
    rather than paying for a second clustering pass over the whole corpus.
    It must be get_events(limit=100) output — the same thing this would fetch."""
    require_database_url()
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(hours=CURRENT_WINDOW_HOURS)
    previous_start = current_start - timedelta(hours=COMPARISON_WINDOW_HOURS)

    articles = _fetch_window_articles(previous_start)
    candidates = _event_candidates(current_start, events) + _entity_candidates(
        articles, current_start
    )

    for c in candidates:
        growth_pct = (
            (c["current_count"] - c["previous_count"]) / c["previous_count"] * 100.0
            if c["previous_count"] > 0
            else None
        )
        c["growth_pct"] = growth_pct
        c["direction"] = _direction(c["previous_count"], growth_pct)
        c["_score"] = _score(c["current_count"], c["previous_count"], growth_pct, c["unique_sources"])

    candidates.sort(key=lambda c: c["_score"], reverse=True)

    selected: list[dict] = []
    covered_by_events: set[str] = set()
    for c in candidates:
        if len(selected) >= limit:
            break
        if c["item_type"] == "event":
            selected.append(c)
            covered_by_events |= c["_current_article_ids"]
        else:
            ids = c["_current_article_ids"]
            overlap = len(ids & covered_by_events) / len(ids) if ids else 0.0
            if overlap > ENTITY_EVENT_OVERLAP_MAX:
                continue
            selected.append(c)

    return [_finalize(item, rank, now) for rank, item in enumerate(selected, start=1)]

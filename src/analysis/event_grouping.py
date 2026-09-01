"""Minimal, deterministic event grouping.

No dedicated event/cluster/story ID exists anywhere in the schema (checked
sql/schema.sql and sql/migrations/ — articles has no such column), and no
embeddings are computed by this pipeline. Events are therefore derived at
query time from three signals that are always real and already available —
never invented, and never based on exact title equality alone:

  - same `primary_category` (topic) — the existing AI classification;
  - published within EVENT_TIME_WINDOW_HOURS of each other (`first_seen_at`);
  - title-token Jaccard similarity >= EVENT_TITLE_SIMILARITY_THRESHOLD, using
    the same whitespace tokenizer as the rest of src/nlp/ with a small
    Hebrew stopword list so generic words ("אמר", "אחרי", ...) don't create
    false matches between unrelated articles.

Articles are joined into events via a union-find over these pairwise edges
(same category + time proximity + title overlap). A cluster of size 1 is not
an "event" — there is nothing to show a timeline for — and is dropped.

This is intentionally the simplest thing that could plausibly work with the
data that exists today, not a replacement for real embeddings/clustering.

That replacement now exists. Articles carry a stored `event_id` computed from
embeddings during ingestion (src/analysis/semantic_events.py,
pipeline/embed_articles.py), and _grouped_articles() below prefers it. The
lexical path is kept as the fallback for exactly one situation: a database
where no embedding pass has run yet, where it is better to show the events it
can find than none at all. It is chosen per-corpus and never per-article, so
there is only ever one notion of what an event is in a given response.

Measured against each other on the same 1,436-article corpus: lexical found 69
events (32 covered by more than one outlet), semantic found 145 (69). Of the
107 article pairs the lexical grouping joined, the semantic grouping keeps 70
and adds 81 the lexical one cannot see, because two outlets covering one story
in Hebrew routinely share no content word at all.

get_events() remains the only entry point.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

from src.analysis.text_keywords import title_token_set
from src.db.config import require_database_url
from src.db.connection import get_connection

EVENT_TIME_WINDOW_HOURS = 72
EVENT_TITLE_SIMILARITY_THRESHOLD = 0.34
MIN_EVENT_SIZE = 2


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    if intersection == 0:
        return 0.0
    return intersection / len(a | b)


class _UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self._parent = {i: i for i in ids}

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


@dataclass
class _Article:
    article_id: str
    source: str
    title: str | None
    primary_category: str | None
    first_seen_at: object  # datetime, kept opaque here
    tokens: set[str]


def _fetch_candidate_articles() -> list[_Article]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                -- Only the columns the clustering and the event summary read.
                -- canonical_url used to be selected here and was never used;
                -- this query runs against every article, so it is pure egress.
                SELECT article_id, source, title, primary_category, first_seen_at
                FROM articles
                WHERE primary_category IS NOT NULL
                ORDER BY first_seen_at
                """
            )
            columns = [d[0] for d in cur.description]
            rows = [dict(zip(columns, r)) for r in cur.fetchall()]
    return [
        _Article(
            article_id=r["article_id"],
            source=r["source"],
            title=r["title"],
            primary_category=r["primary_category"],
            first_seen_at=r["first_seen_at"],
            tokens=title_token_set(r["title"]),
        )
        for r in rows
    ]


def _cluster(articles: list[_Article]) -> dict[str, list[_Article]]:
    from datetime import timedelta

    window = timedelta(hours=EVENT_TIME_WINDOW_HOURS)
    uf = _UnionFind([a.article_id for a in articles])

    # Articles are pre-sorted by first_seen_at, so once b is outside the time
    # window of a, every later article is too — bounds the O(n^2) comparison
    # to nearby-in-time pairs instead of the full cross product.
    for i, a in enumerate(articles):
        if not a.tokens:
            continue
        for b in articles[i + 1 :]:
            if b.first_seen_at - a.first_seen_at > window:
                break
            if b.primary_category != a.primary_category or not b.tokens:
                continue
            if _jaccard(a.tokens, b.tokens) >= EVENT_TITLE_SIMILARITY_THRESHOLD:
                uf.union(a.article_id, b.article_id)

    groups: dict[str, list[_Article]] = {}
    for a in articles:
        root = uf.find(a.article_id)
        groups.setdefault(root, []).append(a)
    return {root: members for root, members in groups.items() if len(members) >= MIN_EVENT_SIZE}


# Every /api/alerts and /api/trending poll re-read the whole article corpus to
# rebuild these groups. The dashboard polls both every 30s from AppShell
# (frontend/src/lib/liveConfig.ts), on every page and in every open tab, so one
# tab pulled ~17 GB/day out of Neon and repeatedly exhausted the project's data
# transfer quota — which failed ingestion runs outright with OperationalError.
#
# The underlying data only changes when ingestion runs, every 6 hours, so
# serving polls from a short-lived cache costs nothing anyone can perceive.
_CACHE_TTL_SECONDS = float(os.environ.get("EVENTS_CACHE_TTL_SECONDS", "300"))

_cache_lock = threading.Lock()
_cached_groups: dict[str, list[_Article]] | None = None
_cached_at: float = 0.0


def _grouped_articles() -> dict[str, list[_Article]]:
    """Clustered corpus, recomputed at most once per _CACHE_TTL_SECONDS.

    The fetch happens while holding the lock, so concurrent callers arriving on
    an expired cache wait for one refresh rather than each starting their own.
    """
    global _cached_groups, _cached_at
    with _cache_lock:
        if _cached_groups is not None and time.monotonic() - _cached_at < _CACHE_TTL_SECONDS:
            return _cached_groups
        articles = _fetch_candidate_articles()
        groups = _stored_groups(articles) or _cluster(articles)
        _cached_groups, _cached_at = groups, time.monotonic()
        return groups


def _stored_groups(articles: list[_Article]) -> dict[str, list[_Article]] | None:
    """Rebuild groups from the persisted event_id, or None if there are none.

    The clustering itself happened during ingestion, where the vectors are
    local. Doing it here instead would mean pulling 1.4k x 384 floats out of
    Neon on every cache miss, and this module's cache exists precisely because
    egress from re-reading the corpus had already exhausted the project's
    transfer quota.

    Returns None - not an empty dict - when nothing is assigned, so that the
    caller can tell "no embedding pass has run" from "the pass ran and found no
    events".
    """
    by_id = {a.article_id: a for a in articles}
    groups: dict[str, list[_Article]] = {}
    for article_id, event_id in _fetch_event_assignments().items():
        article = by_id.get(article_id)
        if article is not None:
            groups.setdefault(event_id, []).append(article)
    if not groups:
        return None
    for members in groups.values():
        members.sort(key=lambda a: a.first_seen_at)
    # A stored event can fall below the minimum if one of its articles lost its
    # category since the clustering ran, and a one-article event has no
    # timeline to show.
    return {k: v for k, v in groups.items() if len(v) >= MIN_EVENT_SIZE}


def _fetch_event_assignments() -> dict[str, str]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT article_id, event_id
                FROM articles
                WHERE event_id IS NOT NULL
                """
            )
            return {row[0]: row[1] for row in cur.fetchall()}


def reset_events_cache() -> None:
    """Drop the cache. For tests, and for callers that must see a write they
    just made (nothing in the read-only API does)."""
    global _cached_groups, _cached_at
    with _cache_lock:
        _cached_groups, _cached_at = None, 0.0


def _event_summary(event_id: str, members: list[_Article]) -> dict:
    members_sorted = sorted(members, key=lambda a: a.first_seen_at)
    # Representative title = the longest headline in the cluster (tends to
    # be the most descriptive, e.g. avoids a truncated wire-style title).
    title = max((m.title for m in members_sorted if m.title), key=len, default=None)
    sources = sorted({m.source for m in members_sorted})
    return {
        "event_id": event_id,
        "title": title,
        "primary_category": members_sorted[0].primary_category,
        "article_count": len(members_sorted),
        "source_count": len(sources),
        "sources": sources,
        "first_seen_at": members_sorted[0].first_seen_at,
        "last_seen_at": members_sorted[-1].first_seen_at,
        "article_ids": [m.article_id for m in members_sorted],
        # Per-article detail (used by trending.py to bucket an event's
        # articles into time windows without a second DB round-trip).
        "members": [
            {"article_id": m.article_id, "source": m.source, "first_seen_at": m.first_seen_at}
            for m in members_sorted
        ],
    }


def get_events(*, category: str | None = None, limit: int = 30) -> list[dict]:
    """Return detected events, most recently updated first.

    `category` filters to events whose topic matches (reuses the same
    primary_category values as the rest of the dashboard).
    """
    groups = _grouped_articles()
    events = [_event_summary(event_id, members) for event_id, members in groups.items()]
    if category:
        events = [e for e in events if e["primary_category"] == category]
    events.sort(key=lambda e: e["last_seen_at"], reverse=True)
    return events[:limit]


def get_event_article_ids(event_id: str) -> list[str] | None:
    """Return the article_ids for one event, or None if it no longer clusters
    into an event (e.g. was a transient grouping)."""
    members = _grouped_articles().get(event_id)
    if members is None:
        return None
    return [m.article_id for m in sorted(members, key=lambda a: a.first_seen_at)]

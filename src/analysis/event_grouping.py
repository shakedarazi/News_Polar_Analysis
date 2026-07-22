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
data that exists today, not a replacement for real embeddings/clustering. If
the system later adds a real cluster/story id or embeddings, callers should
switch to that and this module can be deleted without touching the API
response shape (get_events() below is the only entry point).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.db.config import require_database_url
from src.db.connection import get_connection

EVENT_TIME_WINDOW_HOURS = 72
EVENT_TITLE_SIMILARITY_THRESHOLD = 0.34
MIN_EVENT_SIZE = 2

# Small, title-specific stopword list (Hebrew function words + common verbs
# that appear across unrelated headlines) — deliberately not reused from
# src.nlp.qa._STOPWORDS, which is tuned for question parsing, not headlines.
_TITLE_STOPWORDS = {
    "של", "על", "עם", "את", "זה", "זאת", "אלה", "הם", "הן", "יש", "אין",
    "גם", "רק", "כל", "לא", "כן", "הוא", "היא", "אנחנו", "אתה", "אחרי",
    "לפני", "בין", "מול", "אל", "כי", "אבל", "או", "אמר", "אמרה", "אמרו",
    "כך", "עוד", "כדי", "מה", "מי", "איך", "מתי", "למה",
}
_TOKEN_RE = re.compile(r"[\w֐-׿]+")


def _title_tokens(title: str | None) -> set[str]:
    if not title:
        return set()
    words = _TOKEN_RE.findall(title)
    return {w for w in words if len(w) >= 2 and w not in _TITLE_STOPWORDS}


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
    canonical_url: str
    tokens: set[str]


def _fetch_candidate_articles() -> list[_Article]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT article_id, source, title, primary_category,
                       first_seen_at, canonical_url
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
            canonical_url=r["canonical_url"],
            tokens=_title_tokens(r["title"]),
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
    }


def get_events(*, category: str | None = None, limit: int = 30) -> list[dict]:
    """Return detected events, most recently updated first.

    `category` filters to events whose topic matches (reuses the same
    primary_category values as the rest of the dashboard).
    """
    articles = _fetch_candidate_articles()
    groups = _cluster(articles)
    events = [_event_summary(event_id, members) for event_id, members in groups.items()]
    if category:
        events = [e for e in events if e["primary_category"] == category]
    events.sort(key=lambda e: e["last_seen_at"], reverse=True)
    return events[:limit]


def get_event_article_ids(event_id: str) -> list[str] | None:
    """Return the article_ids for one event, or None if it no longer clusters
    into an event (e.g. was a transient grouping)."""
    articles = _fetch_candidate_articles()
    groups = _cluster(articles)
    members = groups.get(event_id)
    if members is None:
        return None
    return [m.article_id for m in sorted(members, key=lambda a: a.first_seen_at)]

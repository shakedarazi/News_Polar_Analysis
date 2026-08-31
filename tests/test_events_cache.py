"""The event clustering is cached, because polling it was exhausting Neon.

/api/alerts and /api/trending both rebuild the clustering, and the dashboard
polls both every 30s from AppShell — in every open tab. Each rebuild read the
whole article corpus, which repeatedly blew the project's data transfer quota
and failed ingestion runs with OperationalError.

The cache must cut the reads without changing what callers see, so these pin
three things: it expires, it does not read the database while warm, and every
caller still gets its own dicts (the summaries are rebuilt per call, so no
caller can corrupt another's view by mutating a returned list).
"""

from datetime import datetime, timedelta, timezone

import pytest

import src.analysis.event_grouping as eg


def _article(article_id, title, when):
    return eg._Article(
        article_id=article_id,
        source="ynet",
        title=title,
        primary_category="ביטחון",
        first_seen_at=when,
        tokens=eg.title_token_set(title),
    )


@pytest.fixture
def corpus(monkeypatch):
    """Two articles that cluster together, plus a call counter on the fetch."""
    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    rows = [
        _article("a", "פיגוע ירי בצומת גוש עציון הבוקר", now),
        _article("b", "פיגוע ירי בצומת גוש עציון: שני פצועים", now + timedelta(hours=1)),
    ]
    calls = []

    def fake_fetch():
        calls.append(1)
        return rows

    monkeypatch.setattr(eg, "_fetch_candidate_articles", fake_fetch)
    eg.reset_events_cache()
    yield calls
    eg.reset_events_cache()


def test_first_call_reads_the_database(corpus):
    eg.get_events()
    assert len(corpus) == 1


def test_second_call_is_served_from_cache(corpus):
    eg.get_events()
    eg.get_events()
    eg.get_events()
    assert len(corpus) == 1, "polling must not re-read the corpus every time"


def test_get_event_article_ids_shares_the_same_cache(corpus):
    events = eg.get_events()
    eg.get_event_article_ids(events[0]["event_id"])
    assert len(corpus) == 1


def test_cache_expires_after_the_ttl(corpus, monkeypatch):
    eg.get_events()
    # Age the entry past the TTL. Patching time.monotonic to a fixed number is
    # not usable here: it is the process-global clock, and any constant small
    # enough to write is below the real value, so the entry reads as fresh.
    monkeypatch.setattr(eg, "_cached_at", eg._cached_at - eg._CACHE_TTL_SECONDS - 1)
    eg.get_events()
    assert len(corpus) == 2


def test_reset_forces_a_refetch(corpus):
    eg.get_events()
    eg.reset_events_cache()
    eg.get_events()
    assert len(corpus) == 2


def test_results_are_unchanged_by_caching(corpus):
    first = eg.get_events()
    second = eg.get_events()
    assert first == second
    assert first[0]["article_count"] == 2
    assert first[0]["article_ids"] == ["a", "b"]


def test_callers_get_independent_dicts(corpus):
    """A caller mutating what it got back must not poison the next caller."""
    first = eg.get_events()
    first[0]["article_ids"].append("poison")
    first[0]["title"] = "mutated"

    second = eg.get_events()
    assert second[0]["article_ids"] == ["a", "b"]
    assert second[0]["title"] != "mutated"

"""An article page links back to the event it belongs to.

The event page has always linked out to its articles; nothing linked back. The
link has to agree with /events about what an event is, which is why the lookup
scans the shared grouping instead of reading `articles.event_id`: that column
is set by the embedding pass alone (the lexical fallback assigns nothing), and
it stays set on an article whose event has since shrunk below MIN_EVENT_SIZE.
Reading it directly would offer a link to an event the site does not show.
"""

from datetime import datetime, timedelta, timezone

import pytest

import src.analysis.event_grouping as eg

NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def _article(article_id, title, hours, event_id=None):
    return eg._Article(
        article_id=article_id,
        source="ynet",
        title=title,
        primary_category="ביטחון",
        first_seen_at=NOW + timedelta(hours=hours),
        tokens=eg.title_token_set(title),
        event_id=event_id,
    )


@pytest.fixture
def corpus(monkeypatch):
    """Two articles in one stored event, one stranded in an event of its own."""
    rows = [
        _article("a", "פיגוע ירי בצומת גוש עציון הבוקר", 0, event_id="a"),
        _article("b", "שני פצועים בתקרית בדרום הר חברון", 1, event_id="a"),
        _article("c", "עדכון מזג האוויר לסוף השבוע", 2, event_id="c"),
    ]
    calls = []

    def fake_fetch():
        calls.append(1)
        return rows

    monkeypatch.setattr(eg, "_fetch_candidate_articles", fake_fetch)
    eg.reset_events_cache()
    yield calls
    eg.reset_events_cache()


def test_article_resolves_to_its_event(corpus):
    event = eg.find_event_for_article("b")
    assert event is not None
    assert event["event_id"] == "a"
    assert event["article_count"] == 2


def test_article_with_no_event_returns_none(corpus):
    assert eg.find_event_for_article("missing") is None


def test_stored_event_below_the_minimum_is_not_linked(corpus):
    """`c` carries an event_id, but its event has one article and /events drops
    it — so the article page must not offer a link into a 404."""
    assert eg.find_event_for_article("c") is None


def test_lookup_shares_the_corpus_cache(corpus):
    eg.get_events()
    eg.find_event_for_article("a")
    eg.find_event_for_article("b")
    assert len(corpus) == 1, "linking an article must not re-read the corpus"

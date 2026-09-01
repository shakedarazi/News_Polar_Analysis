"""Clustering behaviour, pinned with hand-built vectors.

No model and no database: cluster_by_similarity takes vectors, so every
decision it makes can be stated as an arithmetic fact here.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from src.analysis.semantic_events import (
    CLUSTER_SIMILARITY_THRESHOLD,
    EmbeddedArticle,
    cluster_by_similarity,
)

BASE = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def _unit(*components: float) -> np.ndarray:
    v = np.array(components, dtype=np.float32)
    return v / np.linalg.norm(v)


def _rotated(angle_deg: float) -> np.ndarray:
    """A unit vector at a known angle from (1, 0), so cosine == cos(angle)."""
    rad = np.deg2rad(angle_deg)
    return _unit(float(np.cos(rad)), float(np.sin(rad)))


def _article(article_id, vector, *, category="פוליטי", hours=0):
    return EmbeddedArticle(
        article_id=article_id,
        primary_category=category,
        first_seen_at=BASE + timedelta(hours=hours),
        vector=vector,
    )


def test_empty_input_returns_no_events():
    assert cluster_by_similarity([]) == {}


def test_similar_articles_group_together():
    # cos(10 deg) = 0.985, comfortably above the threshold.
    groups = cluster_by_similarity(
        [_article("a", _rotated(0)), _article("b", _rotated(10))]
    )
    assert list(groups.values()) == [["a", "b"]]


def test_dissimilar_articles_do_not_group():
    # cos(60 deg) = 0.5.
    groups = cluster_by_similarity(
        [_article("a", _rotated(0)), _article("b", _rotated(60))]
    )
    assert groups == {}


def test_threshold_is_the_decision_boundary():
    """Just above the threshold groups; just below does not."""
    above = np.rad2deg(np.arccos(CLUSTER_SIMILARITY_THRESHOLD + 0.02))
    below = np.rad2deg(np.arccos(CLUSTER_SIMILARITY_THRESHOLD - 0.02))
    assert cluster_by_similarity(
        [_article("a", _rotated(0)), _article("b", _rotated(float(above)))]
    )
    assert not cluster_by_similarity(
        [_article("a", _rotated(0)), _article("b", _rotated(float(below)))]
    )


def test_singleton_is_not_an_event():
    groups = cluster_by_similarity([_article("lonely", _rotated(0))])
    assert groups == {}


def test_different_categories_never_join():
    """Near-identical vectors still split when the topic label differs."""
    groups = cluster_by_similarity(
        [
            _article("a", _rotated(0), category="פוליטי"),
            _article("b", _rotated(2), category="ספורט"),
        ]
    )
    assert groups == {}


def test_time_window_splits_a_recurring_story():
    """Identical headlines months apart are two events, not one."""
    same = _rotated(0)
    groups = cluster_by_similarity(
        [_article("march", same, hours=0), _article("september", same, hours=24 * 90)]
    )
    assert groups == {}


def test_event_id_is_the_seed_article_id():
    """Ids are derived from the data, not allocated, so they are reproducible."""
    groups = cluster_by_similarity(
        [_article("later", _rotated(5), hours=3), _article("earliest", _rotated(0))]
    )
    # Seeding walks in time order, so the earliest member names the event.
    assert list(groups) == ["earliest"]


def test_result_is_stable_under_input_permutation():
    articles = [
        _article("a", _rotated(0)),
        _article("b", _rotated(6), hours=1),
        _article("c", _rotated(80), hours=2),
        _article("d", _rotated(84), hours=3),
    ]
    first = cluster_by_similarity(articles)
    for permutation in ([3, 1, 0, 2], [2, 3, 1, 0], [1, 0, 3, 2]):
        assert cluster_by_similarity([articles[i] for i in permutation]) == first


def test_greedy_assignment_does_not_chain():
    """A is close to B, B is close to C, A is far from C: not one event.

    This is the property union-find does not have, and the reason the lexical
    grouping's algorithm was not reused with a cosine edge test.
    """
    articles = [
        _article("a", _rotated(0)),
        _article("b", _rotated(24), hours=1),
        _article("c", _rotated(48), hours=2),
    ]
    groups = cluster_by_similarity(articles, threshold=0.90)
    # cos(24 deg) = 0.914 (in), cos(48 deg) = 0.669 (out).
    assert groups == {"a": ["a", "b"]}


def test_member_is_claimed_by_only_one_event():
    articles = [
        _article("a", _rotated(0)),
        _article("b", _rotated(8), hours=1),
        _article("c", _rotated(16), hours=2),
    ]
    groups = cluster_by_similarity(articles)
    seen = [m for members in groups.values() for m in members]
    assert len(seen) == len(set(seen))


@pytest.mark.parametrize("threshold", [0.86, 0.88, 0.90, 0.92])
def test_raising_the_threshold_never_grows_an_event(threshold):
    """Monotonicity: a stricter cut cannot put more articles in the seed's event."""
    articles = [_article(f"a{i}", _rotated(i * 4), hours=i) for i in range(8)]
    strict = cluster_by_similarity(articles, threshold=threshold)
    loose = cluster_by_similarity(articles, threshold=threshold - 0.04)
    strict_first = len(next(iter(strict.values()), []))
    loose_first = len(next(iter(loose.values()), []))
    assert strict_first <= loose_first


# --- the fallback seam -------------------------------------------------------
#
# get_events() reads stored event ids when an embedding pass has produced them
# and falls back to the lexical grouping when it has not. Getting that choice
# wrong is not a cosmetic bug: mixing the two would put two different notions of
# "event" in one response.

from src.analysis import event_grouping as eg


def _lexical_article(article_id, title, *, source="ynet", hours=0, event_id=None):
    return eg._Article(
        article_id=article_id,
        source=source,
        title=title,
        primary_category="פוליטי",
        first_seen_at=BASE + timedelta(hours=hours),
        tokens=set(title.split()),
        event_id=event_id,
    )


def test_stored_groups_is_none_when_nothing_is_assigned():
    """None, not {} - the caller must be able to tell "no pass has run" from
    "the pass ran and found nothing"."""
    assert eg._stored_groups([_lexical_article("a", "כותרת")]) is None


def test_stored_groups_rebuilds_events_from_ids():
    groups = eg._stored_groups(
        [
            _lexical_article("a", "אחת", event_id="evt"),
            _lexical_article("b", "שתיים", hours=1, event_id="evt"),
        ]
    )
    assert list(groups) == ["evt"]
    assert [m.article_id for m in groups["evt"]] == ["a", "b"]


def test_stored_event_that_lost_a_member_is_dropped():
    """An article can lose its category after clustering ran, leaving an event
    of one. One article is not a timeline."""
    assert eg._stored_groups([_lexical_article("a", "אחת", event_id="evt")]) == {}


def test_grouping_prefers_stored_events_over_lexical(monkeypatch):
    articles = [
        _lexical_article("a", "פיגוע בבקעה צעיר נדקר", event_id="stored"),
        _lexical_article(
            "b", "פיגוע בבקעה צעיר נדקר", source="mako", hours=1, event_id="stored"
        ),
    ]
    monkeypatch.setattr(eg, "_fetch_candidate_articles", lambda: articles)
    eg.reset_events_cache()
    try:
        # Identical titles, so the lexical path would also group these - but
        # under the seed id "a", not the stored id.
        assert list(eg._grouped_articles()) == ["stored"]
    finally:
        eg.reset_events_cache()


def test_grouping_falls_back_to_lexical_when_nothing_is_stored(monkeypatch):
    articles = [
        _lexical_article("a", "פיגוע בבקעה צעיר נדקר"),
        _lexical_article("b", "פיגוע בבקעה צעיר נדקר", source="mako", hours=1),
    ]
    monkeypatch.setattr(eg, "_fetch_candidate_articles", lambda: articles)
    eg.reset_events_cache()
    try:
        groups = eg._grouped_articles()
        assert groups, "identical titles must still cluster lexically"
        assert "stored" not in groups
    finally:
        eg.reset_events_cache()


def test_reading_events_costs_exactly_one_query(monkeypatch):
    """The stored event id rides along on the corpus query rather than adding a
    second one. This module's cache exists because corpus reads were exhausting
    Neon's transfer quota, so a per-cache-miss round trip is the cost it was
    written to avoid."""
    calls = []
    articles = [
        _lexical_article("a", "אחת", event_id="evt"),
        _lexical_article("b", "שתיים", hours=1, event_id="evt"),
    ]

    def counted():
        calls.append(1)
        return articles

    monkeypatch.setattr(eg, "_fetch_candidate_articles", counted)
    eg.reset_events_cache()
    try:
        eg.get_events()
        assert len(calls) == 1
    finally:
        eg.reset_events_cache()

"""The batched bias tally must agree with the per-event path it replaced.

get_event_detail() built `bias_distribution` by counting bias_label over the
rows it fetched for one event; _count_bias_labels() does the same tally for
many events from one lookup table. These pin that equivalence, including the
"no labelled article" case, which the caller treats as "skip this event".
"""

from src.db.events import _bias_distribution, _count_bias_labels


def test_counts_labels_per_event():
    result = _count_bias_labels(
        {"e1": ["a", "b", "c"], "e2": ["d", "e"]},
        {"a": "שמאל", "b": "ימין", "c": "ימין", "d": "מרכז", "e": "מרכז"},
    )
    assert result == {"e1": {"שמאל": 1, "ימין": 2}, "e2": {"מרכז": 2}}


def test_unlabelled_articles_are_ignored():
    result = _count_bias_labels({"e1": ["a", "b"]}, {"a": "ימין"})
    assert result == {"e1": {"ימין": 1}}


def test_event_with_no_labelled_article_is_omitted():
    # get_event_detail returned bias_distribution=None here, and
    # detect_event_polarization skipped the event — absence must mean the same.
    assert _count_bias_labels({"e1": ["a", "b"]}, {}) == {}


def test_no_events():
    assert _count_bias_labels({}, {"a": "ימין"}) == {}


def test_matches_the_row_based_distribution_it_replaced():
    rows = [
        {"article_id": "a", "bias_label": "שמאל"},
        {"article_id": "b", "bias_label": "ימין"},
        {"article_id": "c", "bias_label": None},
    ]
    batched = _count_bias_labels(
        {"e1": [r["article_id"] for r in rows]},
        {r["article_id"]: r["bias_label"] for r in rows if r["bias_label"]},
    )
    assert batched["e1"] == _bias_distribution(rows)

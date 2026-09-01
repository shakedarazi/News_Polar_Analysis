"""Within-event outlet profiling (src/analysis/event_stats.py).

Pure functions over hand-built versions — no DB, no network. What these pin is
the construction, not the corpus: that an outlet votes once per event, that the
deviations of one event cancel, and that the intervals do not quietly widen or
narrow when the code is refactored.
"""

from __future__ import annotations

import pytest

from src.analysis.event_stats import (
    MIN_OBSERVATIONS,
    Version,
    bootstrap_ci,
    deviations_by_source,
    median,
    one_per_source,
    source_profiles,
)


def v(source: str, value: float, *, article_id: str | None = None, weight: int = 0) -> Version:
    return Version(
        article_id=article_id or f"{source}-{value}",
        source=source,
        value=value,
        weight=weight,
    )


def test_median_odd_and_even():
    assert median([3.0, 1.0, 2.0]) == 2.0
    assert median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_one_per_source_keeps_the_most_commented_version():
    versions = [
        v("ynet", 0.10, article_id="a", weight=3),
        v("ynet", 0.90, article_id="b", weight=40),
        v("mako", 0.50, article_id="c", weight=1),
    ]
    kept = {x.source: x.article_id for x in one_per_source(versions)}
    assert kept == {"ynet": "b", "mako": "c"}


def test_one_per_source_breaks_ties_on_article_id():
    """Determinism matters more than which one wins: the same corpus must
    produce the same profile on every request."""
    versions = [
        v("ynet", 0.10, article_id="zzz", weight=5),
        v("ynet", 0.90, article_id="aaa", weight=5),
    ]
    assert [x.article_id for x in one_per_source(versions)] == ["aaa"]


def test_an_outlet_with_five_follow_ups_still_votes_once():
    """The rule that stops one prolific outlet from becoming the median."""
    events = {
        "e1": [v("mako", 0.9, article_id=f"m{i}", weight=i) for i in range(5)]
        + [v("ynet", 0.1, article_id="y1")],
    }
    per_source, counts = deviations_by_source(events)
    assert counts["events_used"] == 1
    assert len(per_source["mako"]) == 1
    assert len(per_source["ynet"]) == 1


def test_deviation_is_distance_from_the_event_median_not_its_mean():
    """The median outlet sits at exactly zero. Using the mean instead would let
    one extreme version drag the baseline it is being measured against."""
    events = {"e1": [v("a", 0.2), v("b", 0.4), v("c", 0.9)]}
    per_source, _ = deviations_by_source(events)
    assert per_source["b"] == [pytest.approx(0.0)]
    assert per_source["a"] == [pytest.approx(-0.2)]
    assert per_source["c"] == [pytest.approx(+0.5)]


def test_a_pair_records_one_comparison_twice():
    """In a two-outlet event the median is the midpoint, so the deviations are
    forced to be +d/2 and -d/2. This is why pair_share is reported."""
    events = {"e1": [v("a", 0.2), v("b", 0.6)]}
    per_source, counts = deviations_by_source(events)
    assert per_source["a"] == [pytest.approx(-0.2)]
    assert per_source["b"] == [pytest.approx(+0.2)]
    assert counts["pair_events"] == 1


def test_single_source_events_are_excluded():
    events = {"solo": [v("ynet", 0.5)], "pair": [v("ynet", 0.5), v("mako", 0.1)]}
    _, counts = deviations_by_source(events)
    assert counts["events_used"] == 1


def test_bootstrap_ci_declines_below_the_observation_floor():
    assert bootstrap_ci([0.1] * (MIN_OBSERVATIONS - 1)) is None
    assert bootstrap_ci([0.1, 0.2, 0.3]) is not None


def test_bootstrap_ci_is_reproducible():
    """A confidence interval that moves when the page is refreshed is not a
    finding. The seed is part of the contract."""
    values = [0.1, -0.2, 0.3, 0.05, -0.01, 0.22]
    assert bootstrap_ci(values) == bootstrap_ci(values)


def test_bootstrap_ci_brackets_the_mean():
    values = [0.10, 0.12, 0.09, 0.11, 0.13, 0.08]
    lo, hi = bootstrap_ci(values)
    assert lo < sum(values) / len(values) < hi


def test_bonferroni_interval_is_never_narrower_than_the_plain_one():
    events = {
        f"e{i}": [v("ynet", 0.30 + i * 0.001), v("mako", 0.10), v("haaretz", 0.20)]
        for i in range(12)
    }
    profile = source_profiles(events)
    assert profile["tests_run"] == 3
    for row in profile["sources"]:
        assert row["ci_low_adjusted"] <= row["ci_low"]
        assert row["ci_high_adjusted"] >= row["ci_high"]


def test_a_consistent_gap_is_significant_and_a_noisy_one_is_not():
    steady = {
        f"e{i}": [v("ynet", 0.40), v("mako", 0.10)] for i in range(20)
    }
    ynet = next(r for r in source_profiles(steady)["sources"] if r["source"] == "ynet")
    assert ynet["mean_deviation"] == pytest.approx(0.15)
    assert ynet["significant"] is True

    noisy = {
        f"e{i}": [v("ynet", 0.40 if i % 2 else 0.00), v("mako", 0.20)] for i in range(20)
    }
    ynet_noisy = next(r for r in source_profiles(noisy)["sources"] if r["source"] == "ynet")
    assert ynet_noisy["significant"] is False


def test_profile_reports_how_much_of_it_is_pairs():
    events = {
        "pair": [v("ynet", 0.4), v("mako", 0.1)],
        "triple": [v("ynet", 0.4), v("mako", 0.1), v("haaretz", 0.2)],
    }
    profile = source_profiles(events)
    assert profile["events_used"] == 2
    assert profile["pair_events"] == 1
    assert profile["pair_share"] == pytest.approx(0.5)


def test_empty_corpus_does_not_divide_by_zero():
    profile = source_profiles({})
    assert profile["sources"] == []
    assert profile["pair_share"] is None
    assert profile["tests_run"] == 0

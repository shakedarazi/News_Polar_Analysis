"""Unit tests for the cross-source framing analytics (no network, no data files).

These cover the parts that would be silently wrong rather than loudly broken:
the within-event baseline, the change-point detector's calibration, and the
guards that stop an under-powered cell from being read as evidence.
"""

import numpy as np
import pytest

from demo.core.framing import (MIN_CELL_EVENTS, MIN_SEGMENT, Event,
                               FramingExtractor, Version, bootstrap_ci,
                               category_mix_deviation, change_point_power,
                               detect_change_point, keyword_jaccard,
                               outlet_deviation, sampling_curve,
                               topic_framing_matrix)


def make_version(source, dominance, lex=None, p85=None, title="כותרת"):
    return Version(
        article_id=f"{source}-{dominance}-{title}", source=source, title=title,
        url="http://x", first_seen_at="2026-08-24 06:00", windows=5,
        mean_dominance=dominance, lex_counts=lex or [1, 1, 0, 0, 0, 0, 0],
        num_comments=10, audience_mean=None, audience_p85=p85,
    )


def make_event(pairs, lexes=None, event_id="e"):
    versions = [make_version(s, d, lex=(lexes[i] if lexes else None), title=f"t{i}")
                for i, (s, d) in enumerate(pairs)]
    return Event(event_id=event_id, versions=versions)


# ---- the within-event baseline -------------------------------------------

def test_deviation_is_measured_against_the_same_event():
    # An outlet that always sits above its own event's median must show a
    # positive deviation even when its absolute numbers are the smaller ones.
    events = [make_event([("a", 0.10), ("b", 0.20)]),
              make_event([("a", 0.90), ("b", 0.50)])]
    devs = outlet_deviation(events, "dominance")
    # Each event has two versions, so the median sits between them.
    assert devs["a"] == pytest.approx([-0.05, 0.20])
    assert devs["b"] == pytest.approx([0.05, -0.20])


def test_single_source_event_is_skipped():
    # With one version there is nothing to compare against; including it would
    # silently contribute a zero and shrink every interval.
    events = [make_event([("a", 0.4)])]
    assert outlet_deviation(events, "dominance") == {}


def test_deviation_ignores_missing_metric():
    events = [make_event([("a", 0.2), ("b", None)])]
    assert outlet_deviation(events, "dominance") == {}


def test_audience_metric_reads_p85():
    versions = [make_version("a", 0.3, p85=0.10), make_version("b", 0.3, p85=0.02)]
    devs = outlet_deviation([Event("e", versions)], "audience_p85")
    assert devs["a"] == pytest.approx([0.04])
    assert devs["b"] == pytest.approx([-0.04])


def test_category_mix_deviation_is_relative_to_event_median():
    events = [make_event([("a", 0.3), ("b", 0.3)],
                         lexes=[[10, 0, 0, 0, 0, 0, 0], [0, 10, 0, 0, 0, 0, 0]])]
    mix = category_mix_deviation(events)
    assert mix["a"][0] > 0 and mix["a"][1] < 0
    assert np.allclose(mix["a"], -mix["b"])


# ---- event topic labelling ------------------------------------------------

def test_event_topic_comes_from_the_median_not_one_outlet():
    # Two versions lean politics, one leans hard to security; the median must
    # not follow the outlier, otherwise the topic label would be set by the
    # very outlet whose deviation we then measure inside it.
    event = make_event([("a", 0.3), ("b", 0.3), ("c", 0.3)],
                       lexes=[[10, 1, 0, 0, 0, 0, 0], [9, 2, 0, 0, 0, 0, 0],
                              [0, 99, 0, 0, 0, 0, 0]])
    assert event.topic_he == "פוליטיקה"


def test_event_topic_none_without_lexicon_hits():
    event = make_event([("a", 0.3), ("b", 0.3)],
                       lexes=[[0] * 7, [0] * 7])
    assert event.topic_he is None


# ---- confidence intervals and the sampling curve --------------------------

def test_bootstrap_ci_needs_three_observations():
    assert bootstrap_ci([0.1, 0.2]) is None
    assert bootstrap_ci([0.1, 0.2, 0.3]) is not None


def test_bootstrap_ci_is_deterministic():
    values = [0.1, -0.2, 0.3, 0.05, -0.1]
    assert bootstrap_ci(values) == bootstrap_ci(values)


def test_sampling_curve_narrows_with_more_evidence():
    rng = np.random.default_rng(4)
    values = list(rng.normal(0.02, 0.1, size=160))
    curve = sampling_curve(values)
    assert curve[0]["width"] > curve[-1]["width"]
    assert curve[-1]["n"] == 160
    # Averaging over subsamples rather than taking a prefix must make the
    # narrowing monotone — that is the whole reason for the resampling.
    widths = [c["width"] for c in curve]
    assert widths == sorted(widths, reverse=True)


def test_sampling_curve_skips_checkpoints_beyond_the_data():
    curve = sampling_curve([0.1, 0.2, 0.3, 0.4])
    assert [c["n"] for c in curve] == [3, 4]


# ---- the topic matrix guards ----------------------------------------------

def test_small_cells_are_never_reported_as_significant():
    # A tiny cell whose interval happens to exclude zero must still be refused:
    # `usable` gates `significant` precisely so a 4-event cell cannot headline.
    events = [make_event([("a", 0.9), ("b", 0.1)], event_id=f"e{i}")
              for i in range(4)]
    cells = topic_framing_matrix(events)
    cell = cells[("a", "פוליטיקה")]
    assert cell.n == 4
    assert cell.ci is not None and cell.ci[1] > 0  # interval excludes zero
    assert not cell.usable
    assert not cell.significant


def test_large_consistent_cell_is_significant():
    events = [make_event([("a", 0.9), ("b", 0.1)], event_id=f"e{i}")
              for i in range(MIN_CELL_EVENTS + 2)]
    cell = topic_framing_matrix(events)[("a", "פוליטיקה")]
    assert cell.usable and cell.significant


# ---- change-point detection ------------------------------------------------

def series(values):
    return [(f"2026-08-{i // 24 + 1:02d} {i % 24:02d}:00", float(v))
            for i, v in enumerate(values)]


def test_change_point_needs_two_full_segments():
    assert detect_change_point(series([0.1] * (2 * MIN_SEGMENT - 1))) is None
    # A perfectly flat series is splittable, so it must come back as an
    # explicit "no change" rather than vanishing from the scan as None.
    flat = detect_change_point(series([0.1] * (2 * MIN_SEGMENT)))
    assert flat is not None
    assert not flat.detected
    assert flat.shift == 0.0


def test_change_point_found_on_a_clear_shift():
    rng = np.random.default_rng(11)
    values = list(rng.normal(0, 0.05, 30)) + list(rng.normal(0.5, 0.05, 30))
    cp = detect_change_point(series(values))
    assert cp.detected
    assert abs(cp.index - 30) <= 3
    assert cp.shift > 0.3


def test_change_point_false_alarm_rate_is_controlled():
    # One noise draw can fire by design (the test is calibrated to ~5%), so
    # assert on the rate across draws rather than on a single lucky seed.
    fired = 0
    for seed in range(40):
        rng = np.random.default_rng(seed)
        cp = detect_change_point(series(rng.normal(0, 1, 60)), iterations=400)
        fired += bool(cp.detected)
    assert fired <= 6  # 40 draws at a nominal 5% alarm rate


def test_permutation_p_value_is_never_zero():
    rng = np.random.default_rng(13)
    values = list(rng.normal(0, 0.01, 30)) + list(rng.normal(50.0, 0.01, 30))
    cp = detect_change_point(series(values), iterations=200)
    assert cp.p_value > 0
    assert cp.detected


def test_change_point_is_order_sensitive_not_value_sensitive():
    # Same multiset of values: ordered as a step it is a change point, shuffled
    # into alternation it must not be.
    step = [0.0] * 25 + [1.0] * 25
    alternating = [0.0, 1.0] * 25
    assert detect_change_point(series(step)).detected
    assert not detect_change_point(series(alternating)).detected


def test_detector_power_grows_with_sample_and_effect():
    small = change_point_power(20, 0.5, iterations=60)
    large = change_point_power(75, 1.5, iterations=60)
    assert large > small
    assert large > 0.8


def test_power_is_zero_when_series_too_short():
    assert change_point_power(4, 2.0, iterations=10) == 0.0


# ---- keyword baseline ------------------------------------------------------

def test_keyword_jaccard_ignores_short_tokens():
    assert keyword_jaccard("על מה זה", "על מה זה") == 0.0  # all tokens < 3 chars


def test_keyword_jaccard_scores_overlap():
    assert keyword_jaccard("חרדים חוסמים כביש", "חרדים חוסמים כביש") == 1.0
    assert keyword_jaccard("חרדים חוסמים כביש", "מטוסים תקפו בסוריה") == 0.0


# ---- LLM response parsing --------------------------------------------------

def test_parse_accepts_fenced_json():
    parsed = FramingExtractor._parse('```json\n{"actor":"ישראל","voice":"active"}\n```')
    assert parsed["actor"] == "ישראל"
    assert parsed["voice"] == "active"


def test_parse_extracts_json_embedded_in_prose():
    parsed = FramingExtractor._parse('הנה הניתוח: {"actor":"טורקיה","voice":"passive"} סוף')
    assert parsed["actor"] == "טורקיה"


def test_parse_normalises_string_null():
    # The model emits the *string* "null" often enough that treating it as a
    # name would put the word "null" in the actor column on screen.
    parsed = FramingExtractor._parse('{"actor":"null","responsibility":"None"}')
    assert parsed["actor"] is None
    assert parsed["responsibility"] is None


def test_parse_rejects_unusable_voice_and_terms():
    parsed = FramingExtractor._parse('{"voice":"maybe","loaded_terms":"טעון"}')
    assert parsed["voice"] is None
    assert parsed["loaded_terms"] == []


def test_parse_returns_none_on_garbage():
    assert FramingExtractor._parse("לא JSON בכלל") is None
    assert FramingExtractor._parse('{"actor": unquoted}') is None

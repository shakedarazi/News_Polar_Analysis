"""Two-axis (Simchon) polarization scoring over comment text.

See docs/adr/0004: this score lives beside polar_ratio and is never blended
with it. The tests that matter most here are the ones pinning that separation.
"""

import math

from src.analysis.aggregation import _weighted_mean, _weighted_quantile
from src.analysis.comments_scoring import score_comment
from src.analysis.polarization_scoring import (
    aggregate_polarization,
    load_polarization_lexicon_for_scoring,
    score_comment_polarization,
)
from src.lexicon.load_lexicon import load_comment_lexicon

LEXICON, VERSION = load_polarization_lexicon_for_scoring()


def _score(text, comment_id="c1"):
    return score_comment_polarization(
        comment_id=comment_id, text=text, polarization_lexicon=LEXICON
    )


# --- the lexicon itself -----------------------------------------------------

def test_expanded_lexicon_shape_is_pinned():
    """A stray edit to polarization.csv should fail here, not in production."""
    assert len(LEXICON) == 2480
    assert sum(1 for c in LEXICON.values() if c == "affective") == 1583
    assert sum(1 for c in LEXICON.values() if c == "issue") == 897


def test_version_is_stable_and_content_derived():
    _, again = load_polarization_lexicon_for_scoring()
    assert VERSION == again
    assert len(VERSION) == 64  # sha256 hex


def test_the_two_polarity_lexicons_are_mostly_disjoint():
    """ADR 0004's premise. If this ever approaches 1.0, the ADR is obsolete."""
    live, _ = load_comment_lexicon()
    shared = set(LEXICON) & live
    assert len(shared) / len(LEXICON) < 0.20


# --- counting ---------------------------------------------------------------

def test_counts_each_axis_separately():
    result = _score("אויב אופוזיציה")
    assert result.affective_count == 1
    assert result.issue_count == 1


def test_polar_count_is_the_sum_of_both_axes():
    for text in ["אויב אופוזיציה", "אויב אויב", "שלום עולם", ""]:
        result = _score(text)
        assert result.polar_count == result.issue_count + result.affective_count


def test_prefixed_forms_match_via_offline_expansion():
    """ה־ is one of the expanded prefixes; no runtime stemming is involved."""
    assert _score("האויב").affective_count == 1
    assert _score("ואויב").affective_count == 1


def test_suffixed_forms_do_not_match():
    """The removed deterministic_matcher stripped suffixes at runtime. This
    pins that we no longer do — expansion covers prefixes only."""
    plain = _score("אויב")
    assert plain.affective_count == 1
    assert _score("אויבים").affective_count == 0


def test_unknown_words_score_zero():
    result = _score("היום יורד גשם בתל אביב")
    assert result.polar_count == 0
    assert result.issue_ratio == 0.0
    assert result.affective_ratio == 0.0


# --- the shared denominator -------------------------------------------------

def test_comment_len_matches_the_single_axis_scorer_exactly():
    """Both ratios must share a denominator or they cannot be compared."""
    live, _ = load_comment_lexicon()
    for text in ["אויב אופוזיציה", "היום יורד גשם", "  רווחים   מרובים  ", ""]:
        mine = _score(text)
        theirs = score_comment(comment_id="c1", text=text, polar_lexicon=live)
        assert mine.comment_len == theirs.comment_len


def test_empty_comment_is_zero_not_a_crash():
    result = _score("")
    assert result.comment_len == 0
    assert result.polar_count == 0
    assert result.issue_ratio == 0.0


def test_ratios_stay_in_range():
    for text in ["אויב", "אויב אויב אויב", "אויב שלום", ""]:
        result = _score(text)
        assert 0.0 <= result.issue_ratio <= 1.0
        assert 0.0 <= result.affective_ratio <= 1.0


def test_a_comment_that_is_all_lexicon_scores_one():
    assert _score("אויב").affective_ratio == 1.0


# --- aggregation ------------------------------------------------------------

def test_aggregate_is_like_weighted_like_audience_mean():
    features = [
        (_score("אויב", "a"), 0),        # weight 1.0
        (_score("שלום עולם", "b"), 99),  # weight 1 + ln(100)
    ]
    weights = [1.0 + math.log(1.0 + likes) for _, likes in features]
    agg = aggregate_polarization(
        "art1", [(f, w) for (f, _), w in zip(features, weights)]
    )
    expected = _weighted_mean([1.0, 0.0], weights)
    assert agg.audience_affective_mean == expected
    assert agg.audience_affective_p85 == _weighted_quantile([0.0, 1.0], [weights[1], weights[0]])


def test_aggregate_of_nothing_is_none_not_zero():
    agg = aggregate_polarization("art1", [])
    assert agg.num_comments == 0
    assert agg.audience_issue_mean is None
    assert agg.audience_affective_mean is None

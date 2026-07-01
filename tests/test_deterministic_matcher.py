"""Tests for deterministic polarization token matcher."""

from src.lexicon.deterministic_matcher import DeterministicLexiconMatcher
from src.lexicon.expand_lexicon import expand_lexicon

BASE_LEXICON = {
    "ממשלה": "issue",
    "רפורמה": "issue",
    "התנגד": "affective",
    "שקר": "affective",
    "שחיתות": "affective",
}


def test_exact_and_prefix_match() -> None:
    matcher = DeterministicLexiconMatcher(expand_lexicon(BASE_LEXICON))
    result = matcher.match_tokens(
        ["ממשלה", "הממשלה", "לרפורמה"],
        BASE_LEXICON,
    )

    assert result["ממשלה"] == "issue"
    assert result["הממשלה"] == "issue"
    assert result["לרפורמה"] == "issue"


def test_suffix_strips_inflected_verb() -> None:
    matcher = DeterministicLexiconMatcher(expand_lexicon(BASE_LEXICON))
    result = matcher.match_tokens(["התנגדה"], BASE_LEXICON)

    assert result["התנגדה"] == "affective"


def test_unmatched_token_returns_none() -> None:
    matcher = DeterministicLexiconMatcher(expand_lexicon(BASE_LEXICON))
    result = matcher.match_tokens(["החליטה"], BASE_LEXICON)

    assert result["החליטה"] is None

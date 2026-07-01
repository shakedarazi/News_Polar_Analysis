"""Tests for offline lexicon expansion."""

from src.lexicon.expand_lexicon import expand_lexicon


def test_expansion_adds_single_prefix_forms() -> None:
    base = {"ממשלה": "issue", "שקר": "affective"}
    expanded = expand_lexicon(base)

    assert expanded["ממשלה"] == "issue"
    assert expanded["הממשלה"] == "issue"
    assert expanded["בממשלה"] == "issue"
    assert expanded["לשקר"] == "affective"


def test_short_lemma_is_not_prefix_expanded() -> None:
    base = {"אם": "issue"}
    expanded = expand_lexicon(base)

    assert expanded == {"אם": "issue"}
    assert "האם" not in expanded

"""Tests for canonical lexicon loading."""

from pathlib import Path

from src.lexicon.load_polarization_lexicon import (
    load_expanded_lexicon,
    load_lexicon,
)

LEXICON_PATH = Path("data/lexicon/polarization.csv")


def test_load_lexicon_from_csv() -> None:
    lexicon = load_lexicon(LEXICON_PATH)

    assert len(lexicon) >= 185
    assert lexicon["ממשלה"] == "issue"
    assert lexicon["בושה"] == "affective"
    assert all(component in {"issue", "affective"} for component in lexicon.values())


def test_expanded_lexicon_is_larger_than_base() -> None:
    base = load_lexicon(LEXICON_PATH)
    expanded = load_expanded_lexicon(LEXICON_PATH)

    assert len(expanded) > len(base)
    assert expanded["הממשלה"] == "issue"

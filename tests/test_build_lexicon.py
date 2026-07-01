"""Tests for polarization lexicon build script."""

from scripts.build_polarization_lexicon import HEBREW_ONLY_ADDITIONS, SKIP_STEMS, build


def test_build_polarization_lexicon_has_approved_rows() -> None:
    rows = build()
    approved = [row for row in rows if row["status"] == "approved" and row["lemma_he"]]
    skipped = [row for row in rows if row["status"] == "skipped"]

    assert len(approved) >= 50
    assert len(skipped) == len(SKIP_STEMS)
    assert any(row["lemma_he"] == "ממשלה" for row in approved)
    assert any(row["lemma_he"] == "ציבור" for row in approved)
    assert any(row["lemma_he"] == "חריפות" for row in approved)
    assert all(row["component"] in {"issue", "affective"} for row in approved)
    assert all(lemma in {row["lemma_he"] for row in approved} for lemma in HEBREW_ONLY_ADDITIONS)

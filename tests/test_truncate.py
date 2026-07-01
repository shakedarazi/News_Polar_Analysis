"""Tests for classification text truncation."""

from src.nlp.truncate import (
    MAX_TEXT_CHARS,
    MIN_TEXT_CHARS,
    truncate_for_classification,
)


def test_short_article_kept_whole():
    text = "פסקה קצרה על בחירות."
    assert truncate_for_classification(text) == text


def test_takes_first_two_paragraphs():
    text = (
        "פסקה ראשונה על פוליטיקה. " + "א" * 200 + "\n\n"
        "פסקה שנייה על כנסת. " + "ב" * 200 + "\n\n"
        "פסקה שלישית שלא אמורה להיכלל. " + "ג" * 500
    )
    result = truncate_for_classification(text)
    assert "פסקה ראשונה" in result
    assert "פסקה שנייה" in result
    assert "פסקה שלישית" not in result


def test_adds_third_paragraph_when_lead_is_short():
    text = "קצר.\n\nעוד קצר.\n\n" + "פסקה ארוכה שלישית. " + "ד" * MIN_TEXT_CHARS
    result = truncate_for_classification(text)
    assert "פסקה ארוכה שלישית" in result


def test_caps_at_max_chars():
    long_para = "א" * 800
    text = f"{long_para}\n\n{long_para}"
    result = truncate_for_classification(text)
    assert len(result) <= MAX_TEXT_CHARS

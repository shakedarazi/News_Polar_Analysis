"""Tests for article classification parsing."""

import json

from src.nlp.categories import CATEGORIES
from src.nlp.classify import _normalize_category, _parse_response


def test_normalize_category_exact():
    assert _normalize_category("ביטחון") == "ביטחון"


def test_normalize_category_unknown():
    assert _normalize_category("מזג אוויר") == "אחר"


def test_parse_response():
    payload = json.dumps(
        {
            "primary_category": "פוליטיקה",
            "confidence": 0.91,
            "rationale": "הכתבה עוסקת בבחירות לכנסת",
        }
    )
    result = _parse_response(payload, "gpt-4o-mini")
    assert result.primary_category == "פוליטיקה"
    assert result.confidence == 0.91
    assert "בחירות" in result.rationale
    assert result.model == "gpt-4o-mini"


def test_categories_count():
    assert len(CATEGORIES) == 9
    assert "אחר" in CATEGORIES

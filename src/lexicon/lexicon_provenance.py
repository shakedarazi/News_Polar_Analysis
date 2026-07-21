"""Provenance labels for polarization.csv notes column."""

from __future__ import annotations

from collections import defaultdict

SOURCE_SIMCHON = "simchon"
SOURCE_ISRAELI = "israeli-supplement"
SOURCE_MEDIA_V2 = "media-v2"
SOURCE_AI_REVIEW = "ai-review"

AI_REVIEW_ADDITIONS = frozenset(
    {
        "בגץ",
        "חטופים",
        "מלחמה",
        "הפגנה",
        "מחאה",
        "חמאס",
        "חיזבאללה",
        "איראן",
        "התנחלות",
        "כיבוש",
        "סיפוח",
        "עזה",
        "גדה",
        "שטחים",
        "מחדל",
        "מושחת",
        "מסית",
        "צביעות",
        "חרפה",
        "ביזיון",
        "הפקרה",
        "שקרן",
        "רעל",
        "הזוי",
        "דיקטטור",
        "שנאה",
        "גזענות",
        "כישלון",
        "שיסוי",
        "נוכל",
        "פאשיסט",
        "גזען",
        "הרס",
        "נמאס",
        "רמאי",
        "בזוי",
    }
)


def build_hebrew_to_english(stem_to_hebrew: dict[str, str]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    for stem, lemma in stem_to_hebrew.items():
        if lemma and stem not in mapping[lemma]:
            mapping[lemma].append(stem)
    return dict(mapping)


def provenance_source(
    lemma: str,
    *,
    stem_to_hebrew: dict[str, str],
    hebrew_only: dict[str, str],
    media_v2: dict[str, str],
) -> str:
    hebrew_to_english = build_hebrew_to_english(stem_to_hebrew)

    if lemma in AI_REVIEW_ADDITIONS:
        return SOURCE_AI_REVIEW
    if lemma in hebrew_to_english:
        return SOURCE_SIMCHON
    if lemma in hebrew_only:
        return SOURCE_ISRAELI
    if lemma in media_v2:
        return SOURCE_MEDIA_V2
    return "unknown"

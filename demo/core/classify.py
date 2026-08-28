"""Shared classification logic — used both by the live agents and by
snapshot/prepare_demo_set.py when it pre-validates the demo arc.

Three methods, in ascending capability (this is the story of the demo):
- baseline: tiny keyword rules + majority-class prior (round 1, "before RAG")
- knn:      weighted vote over vector-index neighbors (rounds 2-3, offline mode)
- llm:      RAG-augmented LLM call (rounds 2-3, live mode; in demo/roles/nova.py)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from demo.core.index import VectorIndex

# Deliberately crude — this is the "before" picture. Majority prior below
# covers everything the keywords miss.
BASELINE_KEYWORDS: dict[str, list[str]] = {
    "ספורט": ["כדורגל", "כדורסל", "מכבי", "הפועל", "ליגה", "שער", "אליפות"],
    "כלכלה": ["בורסה", "שקל", "אינפלציה", "ריבית", "מסחר", "הייטק", "משקיעים"],
    "ביטחון": ["צה\"ל", "צהל", "חיזבאללה", "חמאס", "מטח", "תקיפה", "פיגוע", "כטב\"ם"],
    "פוליטיקה": ["כנסת", "ממשלה", "בחירות", "קואליציה", "אופוזיציה", "ח\"כ"],
    "בינלאומי": ["ארה\"ב", "טראמפ", "איחוד האירופי", "רוסיה", "אוקראינה", "סין"],
    "טכנולוגיה": ["בינה מלאכותית", "סטארטאפ", "אפליקציה", "סייבר"],
    "בידור": ["זמר", "סדרה", "אירוויזיון", "סלב", "קולנוע"],
}
MAJORITY_PRIOR = "ביטחון"  # most frequent class in the corpus


def classify_baseline(title: str, text: str) -> tuple[str, float, str]:
    """Returns (category, confidence, reason_he)."""
    haystack = f"{title} {text[:400]}"
    hits: dict[str, int] = defaultdict(int)
    for cat, words in BASELINE_KEYWORDS.items():
        for w in words:
            if w in haystack:
                hits[cat] += 1
    if hits:
        cat = max(hits, key=lambda c: hits[c])
        conf = min(0.35 + 0.1 * hits[cat], 0.6)
        return cat, conf, f"מילת מפתח ({hits[cat]} התאמות)"
    return MAJORITY_PRIOR, 0.3, "אין התאמות — ניחוש לפי הקטגוריה הנפוצה"


# lexicon c1..c7 → the 9 news categories, where a direct mapping exists
LEXI_TO_NEWS = {0: "פוליטיקה", 1: "ביטחון", 2: "כלכלה", 3: "חברה", 6: "בינלאומי"}


def critic_verdict(pred: str, conf: float,
                   counts: list[int]) -> tuple[str, str | None]:
    """The critic's deterministic core, shared by the live agent (Amit) and by
    prepare_demo.py's arc simulation so the calibrated arc matches showtime.

    Returns (final_category, debate_reason_he | None). A debate is warranted on
    low confidence or on a strong lexicon conflict; the lexicon overrides the
    classifier only when the classifier itself is unsure (< 0.6).
    """
    top_i = max(range(len(counts)), key=lambda i: counts[i]) if any(counts) else None
    mapped = LEXI_TO_NEWS.get(top_i) if top_i is not None else None
    strong = mapped is not None and counts[top_i] >= 4
    reason = None
    if conf < 0.5:
        reason = f"ביטחון נמוך ({conf:.2f})"
    elif strong and mapped != pred:
        reason = f"הלקסיקון מצביע על {mapped}, נובה אמרה {pred}"
    if reason is None:
        return pred, None
    final = mapped if (strong and mapped != pred and conf < 0.6) else pred
    return final, reason


def classify_knn(index: VectorIndex, query_vec: np.ndarray,
                 k: int = 6) -> tuple[str, float, list[dict[str, Any]]]:
    """Weighted neighbor vote. Returns (category, confidence, neighbors)."""
    neighbors = index.query(query_vec, k=k)
    votes: dict[str, float] = defaultdict(float)
    for n in neighbors:
        votes[n["category"]] += max(n["score"], 0.0)
    if not votes:
        return MAJORITY_PRIOR, 0.0, []
    total = sum(votes.values()) or 1.0
    cat = max(votes, key=lambda c: votes[c])
    return cat, votes[cat] / total, neighbors

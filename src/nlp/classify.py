"""AI-based article category classification."""

from __future__ import annotations

from dataclasses import dataclass

from src.nlp.categories import (
    CATEGORIES,
    CATEGORY_DESCRIPTIONS,
)
from src.nlp.llm import ingestion_json
from src.nlp.openai_config import get_ingestion_model
from src.nlp.truncate import truncate_for_classification


@dataclass
class ClassificationResult:
    primary_category: str
    confidence: float
    rationale: str
    model: str


def _build_system_prompt() -> str:
    lines = [
        "אתה מסווג כתבות חדשות בעברית לקטגוריה אחת בלבד.",
        "החזר JSON בלבד עם השדות: primary_category, confidence, rationale.",
        "primary_category חייב להיות בדיוק אחד מהערכים הבאים:",
    ]
    for name in CATEGORIES:
        desc = CATEGORY_DESCRIPTIONS.get(name, "")
        lines.append(f"- {name}: {desc}")
    lines.append(
        "confidence הוא מספר בין 0 ל-1. rationale הוא משפט אחד קצר בעברית המסביר למה."
    )
    lines.append("התבסס רק על הכותרת והטקסט שסופקו. אל תמציא עובדות.")
    return "\n".join(lines)


def _normalize_category(value: str) -> str:
    cleaned = value.strip()
    if cleaned in CATEGORIES:
        return cleaned
    for category in CATEGORIES:
        if category in cleaned:
            return category
    return "אחר"


def _parse_response(data: dict, model: str) -> ClassificationResult:
    category = _normalize_category(str(data.get("primary_category", "אחר")))
    confidence = float(data.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))
    rationale = str(data.get("rationale", "")).strip() or "לא סופק הסבר"
    return ClassificationResult(
        primary_category=category,
        confidence=confidence,
        rationale=rationale,
        model=model,
    )


def classify_article(
    *,
    title: str | None,
    text: str,
    source: str | None = None,
    model: str | None = None,
) -> ClassificationResult:
    model = model or get_ingestion_model()
    body = truncate_for_classification(text)
    data = ingestion_json(
        system=_build_system_prompt(),
        user=(
            f"מקור: {source or 'לא ידוע'}\n"
            f"כותרת: {title or '(ללא כותרת)'}\n\n"
            f"טקסט:\n{body}"
        ),
        model=model,
    )
    return _parse_response(data, model)

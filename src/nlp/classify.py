"""AI-based article category classification."""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.nlp.categories import (
    CATEGORIES,
    CATEGORY_DESCRIPTIONS,
    DEFAULT_MODEL,
)
from src.nlp.openai_config import get_openai_client, require_openai_api_key
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


def _parse_response(content: str, model: str) -> ClassificationResult:
    data = json.loads(content)
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
    model: str = DEFAULT_MODEL,
) -> ClassificationResult:
    require_openai_api_key()
    client = get_openai_client()
    body = truncate_for_classification(text)
    user_content = (
        f"מקור: {source or 'לא ידוע'}\n"
        f"כותרת: {title or '(ללא כותרת)'}\n\n"
        f"טקסט:\n{body}"
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": user_content},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned empty response")
    return _parse_response(content, model)

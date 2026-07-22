"""AI-generated article summaries (summary, key points, topic, entities, sentiment).

Sentiment here describes the tone of the article's own text, and is distinct
from audience polarity (src/analysis/) and political bias (src/nlp/bias.py) —
those are separate, separately-computed signals.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.nlp.categories import DEFAULT_MODEL
from src.nlp.openai_config import require_openai_api_key
from src.nlp.truncate import truncate_for_summary

MAX_KEY_POINTS = 5
MAX_ENTITIES = 8
SENTIMENT_LABELS = ("חיובי", "שלילי", "מעורב", "ניטרלי")


@dataclass
class SummaryResult:
    summary: str
    key_points: list[str]
    topic: str
    entities: list[str]
    sentiment: str
    model: str


def _build_system_prompt() -> str:
    return (
        "אתה מסכם כתבות חדשות בעברית בצורה עובדתית ותמציתית, בהתבסס אך ורק על "
        "הטקסט שסופק. אל תמציא עובדות, מספרים או ציטוטים שלא מופיעים בטקסט.\n\n"
        "החזר JSON בלבד עם השדות הבאים:\n"
        '- "summary": סיכום קצר של 2-4 משפטים.\n'
        f'- "key_points": רשימה של עד {MAX_KEY_POINTS} נקודות מרכזיות (משפטים קצרים).\n'
        '- "topic": הנושא המרכזי של הכתבה, במשפט קצר אחד.\n'
        f'- "entities": רשימה של עד {MAX_ENTITIES} ישויות חשובות המוזכרות בכתבה '
        "(אנשים, ארגונים, מקומות).\n"
        '- "sentiment": הטון הכללי של הכתבה עצמה — בדיוק אחד מהערכים: '
        f'{", ".join(SENTIMENT_LABELS)}.\n\n'
        "sentiment מתאר את הטון של הכתבה עצמה בלבד — לא עמדה פוליטית ולא את "
        "תגובות הקהל."
    )


def _clean_str_list(value: object, max_items: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _normalize_sentiment(value: object) -> str:
    cleaned = str(value).strip()
    return cleaned if cleaned in SENTIMENT_LABELS else "ניטרלי"


def _parse_response(content: str, model: str) -> SummaryResult:
    data = json.loads(content)
    summary = str(data.get("summary", "")).strip()
    if not summary:
        raise ValueError("AI response missing 'summary'")
    return SummaryResult(
        summary=summary,
        key_points=_clean_str_list(data.get("key_points"), MAX_KEY_POINTS),
        topic=str(data.get("topic", "")).strip(),
        entities=_clean_str_list(data.get("entities"), MAX_ENTITIES),
        sentiment=_normalize_sentiment(data.get("sentiment", "ניטרלי")),
        model=model,
    )


def summarize_article(
    *,
    title: str | None,
    text: str,
    source: str | None = None,
    model: str = DEFAULT_MODEL,
) -> SummaryResult:
    require_openai_api_key()
    from openai import OpenAI

    body = truncate_for_summary(text)
    if not body:
        raise ValueError("Article has no content to summarize")

    client = OpenAI()
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

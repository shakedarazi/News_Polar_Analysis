"""AI-estimated political framing/bias for an article's own language.

This is a distinct signal from:
- lexicon audience polarity (src/analysis/) — comment intensity, not lean;
- summary_sentiment (src/nlp/summarize.py) — the article's tone, not politics.

The estimate is produced once per article (like classify_article /
summarize_article), from language and framing cues only (word choice, which
side gets the more sympathetic framing, quote selection) — never from
sentiment or audience polarity. Articles with no clear political framing
(sports, weather, entertainment, ...) are explicitly marked not-applicable
rather than forced onto the scale.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.nlp.llm import user_json
from src.nlp.openai_config import get_user_model
from src.nlp.truncate import truncate_for_summary

# -1.0 = מובהק שמאל, 0.0 = מרכז, +1.0 = מובהק ימין. This scale is defined by
# this analysis itself (no pre-existing bias field/model exists elsewhere in
# the system to map onto — see CLAUDE.md inspection notes in docs/).
BIAS_LABELS = ("שמאל", "מרכז", "ימין")


@dataclass
class BiasResult:
    applicable: bool
    label: str | None  # one of BIAS_LABELS, or None when not applicable
    score: float | None  # -1..1, or None when not applicable
    confidence: float  # 0..1 (0 when not applicable)
    rationale: str
    model: str


def _build_system_prompt() -> str:
    return (
        "אתה מנתח מסגור פוליטי (framing) בכתבות חדשות בעברית, על סמך שפה וניסוח "
        "בלבד — לא על סמך טון רגשי כללי ולא על סמך תגובות קהל.\n\n"
        "בדוק סימנים לשוניים כגון: אילו צדדים מוצגים באור אוהד יותר, בחירת "
        "מילים טעונות, מי מצוטט ומי לא, שימוש במונחים שמזוהים עם מחנה "
        "פוליטי מסוים.\n\n"
        "כתבות רבות (ספורט, מזג אוויר, בידור, תאונות, מדע) אינן מכילות מסגור "
        "פוליטי כלל — עבורן יש להחזיר applicable=false ולא לאלץ ציון.\n\n"
        "החזר JSON בלבד עם השדות:\n"
        '- "applicable": true אם יש בכתבה מסגור פוליטי הניתן לניתוח, אחרת false.\n'
        '- "label": כאשר applicable=true, בדיוק אחד מהערכים: שמאל, מרכז, ימין. '
        "אחרת null.\n"
        '- "score": מספר בין -1 (שמאל מובהק) ל-1 (ימין מובהק), 0 = מרכז. '
        "כאשר applicable=false: null.\n"
        '- "confidence": מספר בין 0 ל-1 המבטא עד כמה ברור הממצא. כאשר '
        "applicable=false: 0.\n"
        '- "rationale": משפט קצר אחד בעברית המסביר אילו סימני שפה/מסגור '
        "הובילו למסקנה (או שאין מסגור פוליטי).\n\n"
        "אל תבסס את הניתוח על טון רגשי, סנטימנט, או עוצמת תגובות קהל — רק על "
        "ניסוח הכתבה עצמה."
    )


def _normalize_label(value: object) -> str | None:
    cleaned = str(value).strip() if value is not None else ""
    return cleaned if cleaned in BIAS_LABELS else None


def _parse_response(data: dict, model: str) -> BiasResult:
    applicable = bool(data.get("applicable", False))

    if not applicable:
        rationale = str(data.get("rationale", "")).strip() or "אין מסגור פוליטי מובהק בכתבה זו."
        return BiasResult(
            applicable=False,
            label=None,
            score=None,
            confidence=0.0,
            rationale=rationale,
            model=model,
        )

    label = _normalize_label(data.get("label"))
    if label is None:
        # Model claimed applicable but didn't give a valid label — treat as
        # not-applicable rather than guessing, per "don't invent bias values".
        return BiasResult(
            applicable=False,
            label=None,
            score=None,
            confidence=0.0,
            rationale="לא ניתן היה לקבוע נטייה פוליטית ברורה עבור כתבה זו.",
            model=model,
        )

    try:
        score = float(data.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(-1.0, min(1.0, score))

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    rationale = str(data.get("rationale", "")).strip() or "לא סופק הסבר"

    return BiasResult(
        applicable=True,
        label=label,
        score=score,
        confidence=confidence,
        rationale=rationale,
        model=model,
    )


def estimate_bias(
    *,
    title: str | None,
    text: str,
    source: str | None = None,
    model: str | None = None,
) -> BiasResult:
    body = truncate_for_summary(text)
    if not body:
        raise ValueError("Article has no content to analyze")

    model = model or get_user_model()
    data = user_json(
        system=_build_system_prompt(),
        user=(
            f"מקור: {source or 'לא ידוע'}\n"
            f"כותרת: {title or '(ללא כותרת)'}\n\n"
            f"טקסט:\n{body}"
        ),
        model=model,
    )
    return _parse_response(data, model)

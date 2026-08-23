"""AI assistant that answers questions strictly from the NewsLens database.

Retrieval is a simple keyword/substring search (no vector store, no external
knowledge) — consistent with the rest of the pipeline's deterministic,
explainable design. The model is instructed to answer only from the supplied
context and to say so explicitly when the data is insufficient.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.db.browse import get_dashboard_stats, search_articles_for_qa
from src.nlp.categories import DEFAULT_MODEL
from src.nlp.openai_config import get_openai_client, require_openai_api_key

MAX_QUESTION_CHARS = 500
MAX_CONTEXT_ARTICLES = 8

# Mirrors frontend/src/lib/format.ts SOURCE_LABELS — included in the LLM context
# so questions phrased with the Hebrew display name (e.g. "הארץ") can be matched
# to the internal source code (e.g. "haaretz") without the model guessing.
SOURCE_LABELS: dict[str, str] = {
    "ynet": "ynet",
    "haaretz": "הארץ",
    "mako": "mako",
    "news12": "חדשות 12",
    "reshet13": "רשת 13",
    "channel14": "ערוץ 14",
}


def _source_display(source: str) -> str:
    label = SOURCE_LABELS.get(source)
    return f"{source} ({label})" if label and label != source else source

_STOPWORDS = {
    "מה", "איך", "כמה", "האם", "מי", "למה", "מתי", "איפה", "של", "על", "עם",
    "את", "זה", "זאת", "אלה", "הם", "הן", "יש", "אין", "גם", "רק", "כל", "לא",
    "כן", "הוא", "היא", "אנחנו", "אתה", "הכי", "יותר", "פחות", "אני", "תגיד",
    "תגידי", "בבקשה", "אלו", "איזה", "איזו",
}


@dataclass
class QaResult:
    answer: str
    sources: list[dict]


def _extract_tokens(question: str) -> list[str]:
    words = re.findall(r"[\w֐-׿]+", question)
    tokens: list[str] = []
    for word in words:
        if len(word) < 2 or word in _STOPWORDS:
            continue
        tokens.append(word)
        if len(tokens) >= 8:
            break
    return tokens


def _format_stats_context(stats: dict) -> str:
    lines = [
        f"סה\"כ כתבות במסד הנתונים: {stats['total_articles']}",
        f"סה\"כ תגובות שנאספו: {stats['total_comments']}",
    ]
    if stats["avg_audience_mean"] is not None:
        lines.append(f"קיטוב ממוצע כללי בתגובות: {stats['avg_audience_mean']:.4f}")
    if stats["by_source"]:
        by_source = ", ".join(
            f"{_source_display(row['source'])}: {row['article_count']} כתבות"
            + (
                f" (קיטוב ממוצע {row['avg_audience_mean']:.4f})"
                if row["avg_audience_mean"] is not None
                else ""
            )
            for row in stats["by_source"]
        )
        lines.append(f"התפלגות לפי מקור: {by_source}")
    if stats["by_category"]:
        by_category = ", ".join(
            f"{row['category']}: {row['article_count']} כתבות" for row in stats["by_category"]
        )
        lines.append(f"התפלגות לפי קטגוריה: {by_category}")
    return "\n".join(lines)


def _format_articles_context(articles: list[dict]) -> str:
    if not articles:
        return "לא נמצאו כתבות רלוונטיות במסד הנתונים לשאלה זו."
    blocks = []
    for i, a in enumerate(articles, start=1):
        polarity = (
            f"{a['audience_mean']:.4f}" if a.get("audience_mean") is not None else "אין נתון"
        )
        blocks.append(
            f"[{i}] article_id={a['article_id']}\n"
            f"    מקור: {_source_display(a['source'])} | "
            f"קטגוריה: {a.get('primary_category') or 'לא מסווג'} | "
            f"תאריך: {a['first_seen_at']} | קיטוב ממוצע בתגובות: {polarity} | "
            f"מספר תגובות: {a.get('num_comments') if a.get('num_comments') is not None else 0}\n"
            f"    כותרת: {a['title'] or '(ללא כותרת)'}\n"
            f"    תקציר: {a['snippet']}"
        )
    return "\n".join(blocks)


_REFUSAL = "אין לי מספיק מידע במסד הנתונים כדי לענות על כך."


def _build_system_prompt() -> str:
    return (
        "אתה עוזר ניתוח נתונים במערכת בשם NewsLens. הנושא היחיד שלך הוא הכתבות, "
        "המקורות, הקטגוריות ומדדי הקיטוב הקיימים במסד הנתונים של המערכת — "
        "ששני הבלוקים 'נתוני סיכום' ו'כתבות רלוונטיות' בהודעת המשתמש מכילים.\n\n"
        "חוקים מוחלטים, שאסור לחרוג מהם בשום מקרה:\n"
        "1. מקור המידע היחיד שמותר לך להשתמש בו הוא הטקסט שסופק לך בהודעת המשתמש "
        "(נתוני הסיכום ורשימת הכתבות). זה כולל גם עובדות שאתה 'יודע' באופן כללי — "
        "אסור להשתמש בהן, אפילו אם הן נכונות במציאות.\n"
        "2. כל שאלה שאינה עוסקת בכתבות/מקורות/קטגוריות/קיטוב שבנתונים שסופקו — "
        "כגון מזג אוויר, ספורט עולמי, מתכונים, תרגום, תכנות, שאלות אישיות, ידע "
        "כללי, חדשות שלא סופקו כאן — חייבת לקבל בדיוק ורק את התשובה: "
        f'"{_REFUSAL}"\n'
        "3. אם הנתונים שסופקו לא כוללים מידע מספיק כדי לענות על שאלה שכן נוגעת "
        f'לתחום המערכת, גם אז השב בדיוק: "{_REFUSAL}"\n'
        "4. אל תנחש, אל תשלים פערים מהיגיון כללי, ואל תמציא מספרים או עובדות.\n\n"
        "כאשר יש מספיק מידע רלוונטי: ענה בעברית, בקצרה ובבהירות, בהתבסס אך ורק "
        "על מה שסופק.\n\n"
        'החזר JSON בלבד עם השדות: "answer" (מחרוזת) ו-"used_article_ids" '
        "(רשימת מזהי article_id מתוך הכתבות שסופקו, עליהן התבססה התשובה בפועל; "
        "רשימה ריקה אם לא נעשה שימוש בכתבה ספציפית)."
    )


def answer_question(question: str) -> QaResult:
    require_openai_api_key()

    question = question.strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("Question is empty")

    stats = get_dashboard_stats()
    tokens = _extract_tokens(question)
    articles = search_articles_for_qa(tokens, limit=MAX_CONTEXT_ARTICLES)

    user_content = (
        f"נתוני סיכום כלליים מהמערכת (לא מסוננים):\n{_format_stats_context(stats)}\n\n"
        f"כתבות רלוונטיות שאותרו במסד הנתונים:\n{_format_articles_context(articles)}\n\n"
        f"שאלת המשתמש:\n{question}\n\n"
        "תזכורת: אם השאלה שלמעלה אינה ניתנת למענה אך ורק מהנתונים שסופקו כאן "
        f'(לדוגמה: שאלה שאינה על כתבות/מקורות/קטגוריות/קיטוב), השב בדיוק: "{_REFUSAL}"'
    )

    client = get_openai_client()
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
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

    by_id = {a["article_id"]: a for a in articles}
    try:
        data = json.loads(content)
        answer = str(data.get("answer", "")).strip()
        used_ids = data.get("used_article_ids") or []
        sources = [by_id[aid] for aid in used_ids if aid in by_id]
    except (json.JSONDecodeError, AttributeError):
        answer = content.strip()
        sources = []

    if not answer:
        answer = _REFUSAL

    return QaResult(answer=answer, sources=sources)

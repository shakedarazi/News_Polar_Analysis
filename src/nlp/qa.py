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
        # The second reading, named by its lexicon. The two are never summed or
        # presented as one number (docs/adr/0004), so the model is handed them
        # labelled and separate rather than blended into a single "polarity".
        research = ""
        if a.get("audience_issue_mean") is not None:
            research = (
                f" | מילון המחקר (סימחון), שפת נושא: {a['audience_issue_mean']:.4f}"
                f", שפת עוינות: {a['audience_affective_mean']:.4f}"
            )
        blocks.append(
            f"[{i}] article_id={a['article_id']}\n"
            f"    מקור: {_source_display(a['source'])} | "
            f"קטגוריה: {a.get('primary_category') or 'לא מסווג'} | "
            f"תאריך: {a['first_seen_at']} | "
            f"מספר תגובות: {a.get('num_comments') if a.get('num_comments') is not None else 0}\n"
            f"    קיטוב בתגובות — רשימת המילים של המערכת: {polarity}{research}\n"
            f"    כותרת: {a['title'] or '(ללא כותרת)'}\n"
            f"    תקציר: {a['snippet']}"
        )
    return "\n".join(blocks)


_REFUSAL = "אין לי מספיק מידע במסד הנתונים כדי לענות על כך."

# What the assistant can actually do, phrased as example questions. Grounded in
# real capabilities (stats, per-source comparison, categories, polarity) — it
# describes the system, so it introduces no outside knowledge about the world
# and does not weaken the "answer only from the database" rule.
_CAPABILITIES = (
    "אני עוזר הניתוח של NewsLens, ואני עונה רק על סמך הכתבות והנתונים שבמסד הנתונים "
    "של המערכת. אפשר לשאול אותי דברים כמו:\n"
    "• כמה כתבות יש במערכת ומאילו מקורות?\n"
    "• מה מדד הקיטוב הממוצע של הארץ לעומת ynet?\n"
    "• אילו כתבות הכי קיטוביות בתגובות שלהן?\n"
    "• כמה כתבות יש בכל קטגוריה?\n"
    "• מה הנושא הכי מסוקר?"
)

_GREETING_REPLY = "היי! " + _CAPABILITIES
_THANKS_REPLY = "בשמחה! " + _CAPABILITIES

# Matched against the whole normalised question, never as a substring — so
# "מה קורה בתחום הביטחון?" stays a real data question and is not swallowed
# here just because it opens with "מה קורה".
_GREETINGS = {
    "היי", "הי", "הייי", "שלום", "אהלן", "הלו", "יו", "מה נשמע", "היי מה נשמע",
    "שלום מה נשמע", "מה שלומך", "מה קורה", "מה המצב", "מה חדש", "בוקר טוב",
    "ערב טוב", "לילה טוב", "צהריים טובים", "hi", "hello", "hey", "yo",
    "good morning", "good evening",
}

_THANKS = {"תודה", "תודה רבה", "thanks", "thank you", "מגניב", "אחלה", "סבבה", "יופי"}

_CAPABILITY_QUESTIONS = {
    "מי אתה", "מה אתה", "מה אתה יודע", "מה אתה יכול", "מה אתה יכול לעשות",
    "מה אתה יודע לעשות", "במה אתה יכול לעזור", "איך אתה יכול לעזור",
    "מה אפשר לשאול", "מה אפשר לשאול אותך", "מה השאלות שאפשר לשאול",
    "עזרה", "help", "מה זה", "מה המערכת הזאת", "מה זאת המערכת",
    "מה הכוונה", "מה זאת אומרת", "לא הבנתי", "תסביר", "תסביר לי",
}


def _normalise(question: str) -> str:
    """Lowercase, drop punctuation/niqqud-free padding, collapse whitespace."""
    stripped = re.sub(r"[?!.,;:\-–—\"'`׳״]+", " ", question.lower())
    return re.sub(r"\s+", " ", stripped).strip()


def _conversational_reply(question: str) -> str | None:
    """Answer small talk about the assistant itself, without an LLM call.

    These are not questions about the world, so refusing them taught users the
    assistant was broken; they are also not questions about the data, so they
    must not reach the model, which is instructed to refuse anything outside
    the supplied context. Returns None for everything else.
    """
    normalised = _normalise(question)
    if not normalised:
        return None
    if normalised in _GREETINGS:
        return _GREETING_REPLY
    if normalised in _THANKS:
        return _THANKS_REPLY
    if normalised in _CAPABILITY_QUESTIONS:
        return _CAPABILITIES
    return None


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
        # Without this the model treated only the article list as "the data"
        # and refused aggregate questions ("מה הנושא הכי מסוקר?") that the
        # stats block answers outright — the refusal then looked like a bug.
        "חשוב, וגובר על נטייה להשיב שאין מידע: בלוק 'נתוני סיכום כלליים' הוא מקור "
        "מלא ותקף בפני עצמו, לא רק רקע. שאלות מצרפיות נענות ממנו ישירות — כמה כתבות "
        "יש, ההתפלגות לפי מקור או לפי קטגוריה, איזה נושא הכי מסוקר (= הקטגוריה עם הכי "
        "הרבה כתבות), איזה מקור הכי פעיל, והקיטוב הממוצע הכללי או לפי מקור. ענה עליהן "
        "מתוך הבלוק הזה גם אם רשימת הכתבות שסופקה אינה רלוונטית לשאלה או ריקה. "
        f'אל תשיב "{_REFUSAL}" כאשר המספר המבוקש מופיע שם.\n\n'
        "כאשר יש מספיק מידע רלוונטי: ענה בעברית, בקצרה ובבהירות, בהתבסס אך ורק "
        "על מה שסופק.\n\n"
        'החזר JSON בלבד עם השדות: "answer" (מחרוזת) ו-"used_article_ids" '
        "(רשימת מזהי article_id מתוך הכתבות שסופקו, עליהן התבססה התשובה בפועל; "
        "רשימה ריקה אם לא נעשה שימוש בכתבה ספציפית)."
    )


def answer_question(question: str) -> QaResult:
    question = question.strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("Question is empty")

    # Before any retrieval or LLM call: greetings and "what can you do" are
    # answered directly. Cheap, instant, and deterministic.
    conversational = _conversational_reply(question)
    if conversational:
        return QaResult(answer=conversational, sources=[])

    require_openai_api_key()
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

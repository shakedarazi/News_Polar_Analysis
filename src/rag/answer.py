"""Answer a question about the corpus, from the corpus.

**The cost shape, which is the design.** A question costs at most one embedding
request and one chat completion. There is no planner call, no query-rewrite
call, no tool-calling loop, and no self-critique pass — each of those is a
round trip that doubles latency on a free Render dyno and buys, on this corpus,
less than it costs.

What replaces a planner is that both kinds of evidence are always fetched.
Aggregate questions ("איזה נושא הכי מסוקר?") are answered from the summary
block; specific ones from the retrieved passages. Deciding which a question
needs would take a model call; fetching both takes two queries against an index
and lets the one call that was always going to happen make the choice. It is
also the fix for the failure the old assistant had, where a question the stats
answered outright was refused because retrieval found nothing relevant.

**Citations.** The model must name the passages it used by number. Those
numbers resolve to article rows the frontend links to, and a number that does
not exist is dropped — so a fabricated citation shows up as a missing link
rather than a plausible one.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from src.db.browse import get_dashboard_stats
from src.nlp.llm import Message, user_json
from src.rag import smalltalk
from src.rag.context import build_user_message
from src.rag.retrieval import retrieve

MAX_QUESTION_CHARS = 500

# How many prior turns the model sees. Four is two exchanges — enough for the
# pronoun in "ומה לגבי הארץ?" to resolve, bounded so a long thread cannot grow
# the prompt without limit.
MAX_HISTORY_TURNS = 4

# Answers to first-message questions are cached: the frontend offers three
# example questions and visitors click them, so the same question arrives
# repeatedly with no history. Follow-ups are not cached — keying on the
# conversation that preceded them would almost never hit.
CACHE_TTL_SECONDS = 300
CACHE_MAX_ENTRIES = 128

REFUSAL = "אין לי מספיק מידע במסד הנתונים כדי לענות על כך."


@dataclass
class Answer:
    answer: str
    sources: list[dict] = field(default_factory=list)
    # True when the vector channel was unavailable and only the lexical half of
    # retrieval ran. Reported rather than hidden: the answer is still grounded,
    # but its recall is not what it should be.
    degraded: bool = False


_cache: dict[str, tuple[float, Answer]] = {}
_cache_lock = threading.Lock()


def reset_cache() -> None:
    """For tests, and for anything that needs immediacy after an ingestion run."""
    with _cache_lock:
        _cache.clear()


def _cache_get(key: str) -> Answer | None:
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        expires_at, answer = entry
        if time.monotonic() >= expires_at:
            del _cache[key]
            return None
        return answer


def _cache_put(key: str, answer: Answer) -> None:
    with _cache_lock:
        if len(_cache) >= CACHE_MAX_ENTRIES:
            # Drop the entry closest to expiry. A full LRU would need access
            # bookkeeping to save a dictionary of at most 128 short strings.
            _cache.pop(min(_cache, key=lambda k: _cache[k][0]), None)
        _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, answer)


def _build_system_prompt() -> str:
    return (
        "אתה עוזר הניתוח של מערכת NewsLens, שאוספת כתבות מאתרי חדשות ישראליים "
        "ומנתחת את הקיטוב בתגובות הקוראים. אתה עונה בעברית.\n\n"
        "מקור המידע היחיד שמותר לך: הטקסט שסופק בהודעת המשתמש — בלוק "
        "'נתוני סיכום כלליים' ובלוק 'קטעים רלוונטיים'. זה כולל גם עובדות שאתה "
        "'יודע' על העולם: אסור להשתמש בהן, גם אם הן נכונות.\n\n"
        "שני הבלוקים תקפים באותה מידה, וזו נקודה שקל לטעות בה:\n"
        "• שאלות מצרפיות — כמה כתבות יש, ההתפלגות לפי מקור או קטגוריה, איזה "
        "נושא הכי מסוקר (= הקטגוריה עם הכי הרבה כתבות), איזה מקור הכי פעיל, "
        "הקיטוב הממוצע — נענות ישירות מבלוק הסיכום, גם אם הקטעים שסופקו אינם "
        "רלוונטיים לשאלה או שאין קטעים כלל.\n"
        "• שאלות על תוכן — מה נכתב על נושא מסוים, איך מקורות שונים סיקרו אותו "
        "— נענות מהקטעים.\n\n"
        "כאשר אתה מסתמך על קטע, צטט את מספרו. אל תמציא מספרי קטעים ואל תצטט "
        "קטע שלא השתמשת בו בפועל.\n\n"
        "מדדי הקיטוב: 'קיטוב בתגובות' הוא ציון בין 0 ל-1 המבוסס על שכיחות "
        "מילים טעונות בתגובות הקוראים לכתבה — הוא מודד עד כמה התגובות מתלהמות, "
        "לא עמדה פוליטית ולא את תוכן הכתבה עצמה. אל תתאר אותו כנטייה פוליטית.\n\n"
        "אם הנתונים שסופקו אינם מספיקים כדי לענות — וכן אם השאלה כלל אינה על "
        "הכתבות, המקורות, הקטגוריות או הקיטוב שבמערכת (מזג אוויר, מתכונים, "
        "תרגום, תכנות, ידע כללי, חדשות שלא סופקו כאן) — השב בדיוק: "
        f'"{REFUSAL}"\n'
        "אל תנחש, אל תשלים פערים מהיגיון כללי, ואל תמציא מספרים או עובדות.\n\n"
        "כאשר יש מספיק מידע: ענה בקצרה ובבהירות, ובמשפטים — לא ברשימת שדות.\n\n"
        'החזר JSON בלבד עם השדות: "answer" (מחרוזת) ו-"citations" (רשימת '
        "מספרי הקטעים שעליהם התבססת בפועל; רשימה ריקה אם ענית מבלוק הסיכום "
        "או לא השתמשת בקטע כלשהו)."
    )


def _resolve_citations(raw: object, passages: list[dict]) -> list[dict]:
    """Map the numbers the model returned onto the passages it was shown.

    Out-of-range numbers are dropped rather than clamped: a citation to a
    passage that does not exist is a fabrication, and pointing it at a real
    article instead would launder it into a plausible-looking link.

    Deduplicated by article, because two chunks of one article are one source
    to a reader.
    """
    if not isinstance(raw, list):
        return []
    sources: list[dict] = []
    seen: set[str] = set()
    for value in raw:
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if not 1 <= index <= len(passages):
            continue
        chunk = passages[index - 1]
        if chunk["article_id"] in seen:
            continue
        seen.add(chunk["article_id"])
        sources.append(
            {
                "article_id": chunk["article_id"],
                "source": chunk["source"],
                "title": chunk["title"],
                "url": chunk.get("url"),
                "primary_category": chunk.get("primary_category"),
                "first_seen_at": chunk["first_seen_at"],
                "snippet": chunk["text"][:300],
                "audience_mean": chunk.get("audience_mean"),
                "audience_p85": chunk.get("audience_p85"),
                "num_comments": chunk.get("num_comments"),
            }
        )
    return sources


def _recent_history(history: list[Message]) -> list[Message]:
    """The last few turns, always starting on a user turn so the transcript the
    model reads is a conversation rather than a reply with no question."""
    recent = list(history)[-MAX_HISTORY_TURNS:]
    while recent and recent[0].role != "user":
        recent.pop(0)
    return recent


def _previous_question(history: list[Message]) -> str | None:
    for turn in reversed(history):
        if turn.role == "user":
            return turn.content
    return None


def answer_question(question: str, history: list[Message] | None = None) -> Answer:
    question = question.strip()[:MAX_QUESTION_CHARS]
    if not question:
        raise ValueError("Question is empty")

    history = _recent_history(history or [])

    # Before any retrieval, embedding or model call: greetings and "what can
    # you do" are answered directly. Instant, free, and deterministic.
    canned = smalltalk.reply_for(question, has_history=bool(history))
    if canned:
        return Answer(answer=canned)

    cache_key = smalltalk.normalise(question) if not history else None
    if cache_key:
        cached = _cache_get(cache_key)
        if cached:
            return cached

    found = retrieve(question, previous_question=_previous_question(history))
    stats = get_dashboard_stats()
    user_message, passages = build_user_message(
        question=question, stats=stats, chunks=found.chunks
    )

    data = user_json(
        system=_build_system_prompt(),
        user=user_message,
        history=history,
    )

    answer = Answer(
        answer=str(data.get("answer", "")).strip() or REFUSAL,
        sources=_resolve_citations(data.get("citations"), passages),
        degraded=found.degraded,
    )
    if cache_key:
        _cache_put(cache_key, answer)
    return answer

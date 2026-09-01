"""Replies that need neither retrieval nor a model.

Users opening with "היי מה נשמע?" were told the database had insufficient
information, which reads as a broken assistant. These are not questions about
the world, so refusing them is wrong; they are not questions about the data
either, so they must not reach a model that is instructed to refuse anything
outside its context.

Matching is against the whole normalised message, never as a substring, so
"מה קורה בתחום הביטחון?" stays a real question and is not swallowed here just
because it opens with "מה קורה". tests/test_qa_conversational.py pins both
sides of that line.
"""

from __future__ import annotations

import re

# What the assistant can actually do, phrased as example questions. Grounded in
# real capabilities, so it introduces no outside knowledge about the world and
# does not weaken the "answer only from the database" rule.
CAPABILITIES = (
    "אני עוזר הניתוח של NewsLens, ואני עונה רק על סמך הכתבות והנתונים שבמסד הנתונים "
    "של המערכת. אפשר לשאול אותי דברים כמו:\n"
    "• כמה כתבות יש במערכת ומאילו מקורות?\n"
    "• מה מדד הקיטוב הממוצע של הארץ לעומת ynet?\n"
    "• מה נכתב על יוקר המחיה בכתבות שנאספו?\n"
    "• איך מקורות שונים סיקרו את אותו אירוע?\n"
    "• כמה כתבות יש בכל קטגוריה, ומה הנושא הכי מסוקר?"
)

GREETING_REPLY = "היי! " + CAPABILITIES
THANKS_REPLY = "בשמחה! " + CAPABILITIES

_GREETINGS = frozenset(
    {
        "היי", "הי", "הייי", "שלום", "אהלן", "הלו", "יו", "מה נשמע", "היי מה נשמע",
        "שלום מה נשמע", "מה שלומך", "מה קורה", "מה המצב", "מה חדש", "בוקר טוב",
        "ערב טוב", "לילה טוב", "צהריים טובים", "hi", "hello", "hey", "yo",
        "good morning", "good evening",
    }
)

_THANKS = frozenset(
    {"תודה", "תודה רבה", "thanks", "thank you", "מגניב", "אחלה", "סבבה", "יופי"}
)

_CAPABILITY_QUESTIONS = frozenset(
    {
        "מי אתה", "מה אתה", "מה אתה יודע", "מה אתה יכול", "מה אתה יכול לעשות",
        "מה אתה יודע לעשות", "במה אתה יכול לעזור", "איך אתה יכול לעזור",
        "מה אפשר לשאול", "מה אפשר לשאול אותך", "מה השאלות שאפשר לשאול",
        "עזרה", "help", "מה זה", "מה המערכת הזאת", "מה זאת המערכת",
    }
)

# Deliberately not in _CAPABILITY_QUESTIONS any more. "מה הכוונה?" and
# "לא הבנתי" were answered with the capabilities blurb because the assistant
# was single-turn and could not resolve them; now it has the history, so they
# are ordinary follow-ups and belong to the model.
_NEEDS_HISTORY = frozenset(
    {"מה הכוונה", "מה זאת אומרת", "לא הבנתי", "תסביר", "תסביר לי"}
)


def normalise(message: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    stripped = re.sub(r"[?!.,;:\-–—\"'`׳״]+", " ", message.lower())
    return re.sub(r"\s+", " ", stripped).strip()


def reply_for(message: str, *, has_history: bool = False) -> str | None:
    """A canned reply, or None to send the message on to retrieval."""
    normalised = normalise(message)
    if not normalised:
        return None
    if normalised in _GREETINGS:
        return GREETING_REPLY
    if normalised in _THANKS:
        return THANKS_REPLY
    if normalised in _CAPABILITY_QUESTIONS:
        return CAPABILITIES
    if normalised in _NEEDS_HISTORY and not has_history:
        # First message in the thread: there is nothing to explain yet, so the
        # capabilities blurb is still the most useful thing to say.
        return CAPABILITIES
    return None

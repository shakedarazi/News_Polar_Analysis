"""Media-framing variables per article, plus the verifier that grounds them.

This is the one AI step in the system whose output is checked against the text
it claims to describe before anything reaches a screen. Three signals already
exist and this is none of them:

- lexicon polarity (src/analysis/) — how charged the audience is, per comment;
- bias_label (src/nlp/bias.py) — which political camp the language leans to;
- summary_sentiment (src/nlp/summarize.py) — the article's tone.

Framing is structural rather than evaluative: *who* is named as performing the
action, *to whom* responsibility is attributed, whether the sentence is active
or passive, and whose point of view the lead opens from. Two outlets can carry
identical sentiment and identical political lean and still differ here — that
difference is the thing a lexicon cannot see, which is why it is worth an
LLM call.

Extraction and verification deliberately share ONE constant,
EXTRACT_LEAD_CHARS. See the note on it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.nlp.llm import user_json
from src.nlp.openai_config import get_user_model

# The slice of the article the model reads, and — the same number — the slice
# the verifier searches. These must not drift apart: when they were 500 and
# 600, a term that appeared only in characters 500-600 passed verification even
# though the model never saw it, which is precisely the invention the verifier
# exists to catch. Checking the title alone is the opposite failure: it rejects
# terms the model was legitimately reading.
EXTRACT_LEAD_CHARS = 500

# Five short fields. The cap is a cost bound, not a quality dial.
FRAMING_MAX_TOKENS = 300

VOICES = ("active", "passive")


@dataclass
class FramingResult:
    """A verified extraction. Everything here has survived grounding."""

    actor: str | None
    actor_grounded: bool
    responsibility: str | None
    loaded_terms: list[str]
    # Terms the model returned that do not occur in the text it was given.
    # Kept rather than discarded: they are the evidence that the check runs.
    dropped_terms: list[str]
    voice: str | None
    lead_perspective: str | None
    model: str
    lead_chars: int = EXTRACT_LEAD_CHARS
    violations: list[str] = field(default_factory=list)


def _build_system_prompt() -> str:
    return (
        "אתה מנתח מסגור תקשורתי (framing) בידיעות חדשות בעברית. בהינתן כותרת "
        "ופסקה ראשונה, החזר JSON בלבד עם השדות הבאים בדיוק:\n"
        '- "actor": מי מוצג כמבצע הפעולה בכותרת. null אם הניסוח סביל ואין '
        "מבצע מפורש.\n"
        '- "responsibility": למי מיוחסת האחריות למצב המתואר. null אם לא '
        "מיוחסת אחריות לאיש.\n"
        '- "loaded_terms": רשימת מילות הערכה טעונות שמופיעות בכותרת בלבד — '
        "שמות תואר או כינויים שיפוטיים. רשימה ריקה אם הכותרת ניטרלית.\n"
        '- "voice": active או passive.\n'
        '- "lead_perspective": מנקודת מבט של מי נפתחת הידיעה.\n\n'
        "כלל מחייב: כל ערך מחרוזת שאתה מחזיר חייב להופיע בטקסט שקיבלת "
        "כלשונו. אל תנסח מחדש, אל תתרגם ואל תוסיף מילים. אם אינך מוצא ערך "
        "בטקסט — החזר null."
    )


def _clean_string(value: object) -> str | None:
    """The model sometimes writes the word "null" instead of JSON null."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.lower() in ("null", "none", "לא ידוע", "-"):
        return None
    return cleaned


def _normalise(text: str | None) -> str:
    """Drop quote marks and collapse whitespace, so a term lifted out of a
    headline still matches the headline it was lifted from."""
    return re.sub(r"\s+", " ", re.sub(r"[\"״“”'׳]", "", text or "")).strip()


def verify_framing(
    *,
    actor: str | None,
    loaded_terms: list[str],
    title: str | None,
    text: str,
) -> tuple[str | None, bool, list[str], list[str], list[str]]:
    """Ground an extraction in the text the extractor was given.

    This is string containment, not a second opinion from a model. A loaded
    term must occur in the headline or lead; a named actor must occur there
    too. Both errors it can make fall the same way — less on the screen, never
    more — which is the property that makes it worth keeping even though it
    rejects some correct answers (a model that writes "מברכת" for a headline's
    "המבורכת" is right, and is still dropped).

    Returns (actor, actor_grounded, kept_terms, dropped_terms, violations).
    """
    haystack = _normalise(f"{title or ''} {(text or '')[:EXTRACT_LEAD_CHARS]}")
    kept: list[str] = []
    dropped: list[str] = []
    violations: list[str] = []

    for term in loaded_terms:
        if not isinstance(term, str) or not term.strip():
            continue
        if _normalise(term) in haystack:
            kept.append(term.strip())
        else:
            dropped.append(term.strip())
            violations.append(f"מילה טעונה שאינה בטקסט: {term.strip()}")

    actor_grounded = True
    if actor:
        # Proper nouns get shortened on second mention ("טום באראק" -> "באראק"),
        # so requiring the whole string would reject correct answers. But
        # accepting ANY single word is too weak in the other direction: it
        # grounds the invented "ראש הממשלה נתניהו" on the word "הממשלה"
        # occurring somewhere in the lead. The rule is therefore a majority —
        # more than half the name's substantial words must actually be there.
        # Words under three characters are prepositions and would match
        # anything, so they do not count either way.
        words = [w for w in _normalise(actor).split() if len(w) >= 3]
        matched = sum(1 for w in words if w in haystack)
        actor_grounded = bool(words) and matched * 2 >= len(words)
        if not actor_grounded:
            violations.append(f"מבצע שאינו מופיע בטקסט: {actor}")

    return actor, actor_grounded, kept, dropped, violations


def parse_framing(data: dict, *, title: str | None, text: str, model: str) -> FramingResult:
    """Shape and ground one extraction. Takes the parsed object: decoding the
    model's JSON — including the Hebrew-acronym quote repair this function used
    to own — belongs to src/nlp/llm.py, which every AI step now goes through."""
    raw_terms = data.get("loaded_terms")
    if not isinstance(raw_terms, list):
        raw_terms = []

    voice = _clean_string(data.get("voice"))
    if voice not in VOICES:
        voice = None

    actor, grounded, kept, dropped, violations = verify_framing(
        actor=_clean_string(data.get("actor")),
        loaded_terms=raw_terms,
        title=title,
        text=text,
    )

    return FramingResult(
        actor=actor,
        actor_grounded=grounded,
        responsibility=_clean_string(data.get("responsibility")),
        loaded_terms=kept,
        dropped_terms=dropped,
        voice=voice,
        lead_perspective=_clean_string(data.get("lead_perspective")),
        model=model,
        violations=violations,
    )


def extract_framing(
    *,
    title: str | None,
    text: str,
    model: str | None = None,
) -> FramingResult:
    lead = (text or "").strip()[:EXTRACT_LEAD_CHARS]
    if not lead:
        raise ValueError("Article has no content to analyze")

    model = model or get_user_model()
    data = user_json(
        system=_build_system_prompt(),
        user=f"כותרת: {title or '(ללא כותרת)'}\nפתיח: {lead}",
        model=model,
        max_tokens=FRAMING_MAX_TOKENS,
    )
    return parse_framing(data, title=title, text=text, model=model)

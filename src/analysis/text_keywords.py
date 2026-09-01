"""Shared Hebrew content-word tokenization.

Used by event_grouping.py (title-token Jaccard similarity, for clustering
articles into an "event"), trending.py (n-gram entity/keyword frequency, for
surfacing real trending entities instead of generic categories), and
src/rag/retrieval.py (the terms the lexical half of retrieval searches for) —
kept in one place so they stay consistent instead of drifting into three
different stopword lists and three different tokenizers.

The stopword list was written against headlines, and reads that way, but every
word in it is a word a *question* is equally better off without: the question
words ("מה", "כמה", "האם") are already there, and the journalism verbs
("הודיע", "דיווח") match thousands of chunks while narrowing nothing.
"""

from __future__ import annotations

import re

# Hebrew function words + common verbs and generic journalism words that
# appear across unrelated headlines — filtered out so they don't create
# false title-similarity matches or show up themselves as "trending
# entities" (e.g. "דיווח" recurs in dozens of unrelated headlines).
TITLE_STOPWORDS = frozenset(
    {
        "של", "על", "עם", "את", "זה", "זאת", "אלה", "הם", "הן", "יש", "אין",
        "גם", "רק", "כל", "לא", "כן", "הוא", "היא", "אנחנו", "אתה", "אחרי",
        "לפני", "בין", "מול", "אל", "כי", "אבל", "או", "אמר", "אמרה", "אמרו",
        "כך", "עוד", "כדי", "מה", "מי", "איך", "מתי", "למה", "יותר", "פחות",
        "כמה", "האם", "כנגד", "נגד", "לגבי", "בעקבות", "במהלך", "לאחר",
        "תוך", "ללא", "עד", "כאשר", "אז", "שוב", "כבר", "עדיין", "אך",
        "אותו", "אותה", "אותם", "אותן",
        "דיווח", "דיווחים", "דיווחה", "דיווחו", "נחשף", "נחשפה", "נחשפו",
        "פרסום", "פרסם", "פרסמה", "פרסמו", "בלעדי", "צפו", "לצפייה",
        "חדש", "חדשה", "חדשות", "ראשונה", "ראשון", "לראשונה",
        "הודיע", "הודיעה", "הודיעו", "טען", "טענה", "טענו",
        "הוסיף", "הוסיפה", "הוסיפו", "ציין", "ציינה", "ציינו",
        "מדובר", "לדברי", "דובר", "דוברת",
        # Casualty/severity outcome words — recur across unrelated incident
        # headlines (stabbings, accidents, shootings) so they pass the
        # recurrence threshold without naming any real entity/topic.
        "למוות", "קשה", "קל", "קלה", "בינוני", "בינונית", "אנוש", "אנושה",
        "נפצע", "נפצעה", "נפצעו", "נהרג", "נהרגה", "נהרגו",
        "נדקר", "נדקרה", "נדקרו", "נורה", "נורתה", "נורו",
        "נעצר", "נעצרה", "נעצרו", "מצבו", "מצבה",
        "פצוע", "פצועה", "פצועים", "חשד", "חשוד", "חשודה", "חשודים",
        "מעורב", "מעורבות",
        # Generic nouns/descriptors that recur across unrelated crime and
        # accident headlines ("גבר נדקר ליד תחנת...", "רכב פגע ב...") — real
        # topics/entities are what's *around* these words (a place, a name),
        # never the words themselves.
        "סמוך", "ליד", "עקב", "שני", "שתי", "גבר", "אישה", "נשים",
        "צעיר", "צעירה", "נער", "נערה", "ילד", "ילדה", "אדם", "אנשים",
        "תושב", "תושבת", "תושבים", "שוטר", "שוטרים", "רכב", "תחנה", "תחנת",
        "כוח", "כוחות", "חוץ", "החוץ", "במזרח", "במערב", "בדרום", "בצפון",
        "בית", "הבית",
    }
)

# Words that are only meaningful as part of a longer phrase (e.g. "בן גביר")
# and pure noise on their own ("בן 80"). Kept in the token stream so 2-grams
# containing them still form, but never emitted as a standalone 1-gram.
CONNECTOR_WORDS = frozenset({"בן", "בת", "בני", "בנות"})

MIN_TOKEN_LEN = 2
# Word chars plus internal gershayim/quote for Hebrew abbreviations
# (צה"ל, ארה"ב, שב"כ) — without this, "צה\"ל" fragments into "צה" + "ל".
_TOKEN_RE = re.compile(r'[\w֐-׿]+(?:["\'׳״][\w֐-׿]+)*')


def tokenize_title(title: str | None) -> list[str]:
    """Ordered, stopword-filtered tokens from a title (order matters for n-grams)."""
    if not title:
        return []
    words = _TOKEN_RE.findall(title)
    return [
        w
        for w in words
        if len(w) >= MIN_TOKEN_LEN and w not in TITLE_STOPWORDS and not w.isdigit()
    ]


def title_token_set(title: str | None) -> set[str]:
    return set(tokenize_title(title))


def extract_ngrams(title: str | None, max_n: int = 2) -> list[str]:
    """Contiguous 1..max_n word phrases from the stopword-filtered token
    sequence — e.g. "איראן" (1-gram) and "בן גביר" (2-gram). Only adjacent
    *surviving* tokens are combined, so a stopword never ends up glued into
    a phrase, and a lone CONNECTOR_WORDS token is never emitted by itself."""
    tokens = tokenize_title(title)
    grams: list[str] = []
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            gram_tokens = tokens[i : i + n]
            if n == 1 and gram_tokens[0] in CONNECTOR_WORDS:
                continue
            grams.append(" ".join(gram_tokens))
    return grams

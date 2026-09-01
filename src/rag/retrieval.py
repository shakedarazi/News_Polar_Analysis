"""Find the passages that bear on a question.

Two channels, fused. Neither is sufficient on its own for this corpus:

- **Semantic.** "מה קורה עם יוקר המחיה?" should reach a chunk that says
  "מחירי הדיור עלו ב-4%", which shares no word with the question. The old
  assistant's substring search could not see it, and no threshold on word
  overlap ever could.
- **Lexical.** A vector search for "בן גביר" retrieves chunks about the
  political camp he belongs to before chunks that name him. Rare proper nouns
  are exactly where dense retrieval is weakest and a substring match is exact.

The fusion is Reciprocal Rank Fusion, done in SQL — see src/db/chunks.py for
why the ranking cannot happen in Python on the API host.

**Follow-up questions get no extra model call.** "ומה לגבי הארץ?" embeds to
nothing useful alone, so the previous user turn is prepended to form the search
text. That is one string concatenation instead of a query-rewriting round trip,
which for a two-turn follow-up is most of what a rewrite would have produced.
It is genuinely weaker when the thread has drifted over several turns and the
pronoun refers to something said four messages ago; the answer call still sees
the full history, so it can say so rather than answer the wrong question.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.analysis.text_keywords import tokenize_title
from src.db.chunks import search_chunks
from src.rag.embedding import embed_query, to_literal

# Chunks handed to the model. Eight passages of ~700 characters is roughly
# 5,600 characters of evidence — enough to compare three or four outlets on one
# story, and a bounded prompt cost per question.
DEFAULT_CHUNK_LIMIT = 8

# More terms than this and the lexical channel matches everything, which is the
# same as matching nothing once the ranks are fused.
MAX_TERMS = 8


@dataclass
class Retrieval:
    """What the search found, and how it had to be found."""

    chunks: list[dict] = field(default_factory=list)
    terms: list[str] = field(default_factory=list)
    search_text: str = ""
    # True when the vector channel was unavailable and the result is lexical
    # only. Surfaced rather than swallowed: an answer built on half the search
    # is worth knowing about in a log, and the API reports it.
    degraded: bool = False
    degraded_reason: str | None = None


def query_terms(text: str) -> list[str]:
    """Content words to search for, in order of appearance.

    Deduplicated while preserving order — a question that repeats a name should
    not spend two of its eight term slots on it.
    """
    seen: set[str] = set()
    terms: list[str] = []
    for token in tokenize_title(text):
        if token in seen:
            continue
        seen.add(token)
        terms.append(token)
        if len(terms) >= MAX_TERMS:
            break
    return terms


def search_text_for(question: str, previous_question: str | None = None) -> str:
    """The text the search runs on: the question, after a short follow-up has
    borrowed its subject from the turn before it."""
    question = question.strip()
    previous = (previous_question or "").strip()
    if not previous:
        return question
    return f"{previous} {question}"


def retrieve(
    question: str,
    *,
    previous_question: str | None = None,
    limit: int = DEFAULT_CHUNK_LIMIT,
    source: str | None = None,
    category: str | None = None,
) -> Retrieval:
    """Run both channels and fuse them. Never raises for a retrieval failure.

    An embedding provider that is down, rate-limited or unconfigured degrades
    the answer; it must not break it. The lexical channel needs no provider and
    no key, so there is always something to fall back to — the same
    fallback-rather-than-nothing choice ADR 0005 made for event grouping.
    """
    text = search_text_for(question, previous_question)
    terms = query_terms(text)

    vector_literal: str | None = None
    degraded_reason: str | None = None
    try:
        vector_literal = to_literal(embed_query(text))
    except Exception as exc:  # noqa: BLE001 - provider errors are not ours to type
        degraded_reason = str(exc)

    chunks = search_chunks(
        query_vector=vector_literal,
        terms=terms,
        limit=limit,
        source=source,
        category=category,
    )
    return Retrieval(
        chunks=chunks,
        terms=terms,
        search_text=text,
        degraded=vector_literal is None,
        degraded_reason=degraded_reason,
    )

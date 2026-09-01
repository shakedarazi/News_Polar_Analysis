"""Split an article into the passages that get embedded and retrieved.

Why chunks and not whole articles. The corpus embedding that already exists
(`articles.title_embedding`, src/analysis/embeddings.py) covers the title plus
400 characters, because its job is to decide whether two articles are the same
*event*. A question like "מה נאמר על מחירי הדיור?" is answered by one paragraph
somewhere in the middle of an article, and a single vector for a 4,000-character
article is dominated by whatever the article is mostly about. Those are
different jobs and they want different granularity, which is why this is a
second table rather than a reuse of that column.

Sentence boundaries come from src/nlp/sentence_splitter.py — the same splitter
the analysis windows use. A second definition of "where a sentence ends" would
be a second answer to a question this codebase has already settled.

Three properties are deliberate:

- **Every chunk carries its title into the embedding.** A paragraph reading
  "הוא הוסיף כי מדובר בצעד הכרחי" says almost nothing on its own; with the
  headline in front of it, the vector lands near the story it belongs to. The
  title is prepended to the *embedded* text only — `text` stays the passage as
  it was written, because that is what gets quoted back to a reader.
- **One sentence of overlap.** A claim split across a chunk boundary is
  otherwise retrievable from neither side.
- **Chunking is pure.** No database, no model, no network — so the split can be
  tested by reading it.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.nlp.sentence_splitter import split_sentences

# Roughly a paragraph. Small enough that a retrieved chunk is mostly about one
# thing, large enough that a claim usually sits inside one chunk rather than
# being spread over three. Characters rather than tokens because Hebrew
# tokenises unevenly and the number is a budget, not a contract.
TARGET_CHUNK_CHARS = 700

# A chunk shorter than this is not worth its own row or its own vector — it is
# a stray fragment ("צילום: רויטרס"), and retrieving it wastes context budget.
# It is not dropped: it is merged into the chunk before it.
MIN_CHUNK_CHARS = 120

# One sentence, carried forward. Two was measurably more storage for the same
# recall on this corpus; zero loses claims that straddle a boundary.
OVERLAP_SENTENCES = 1

# A single sentence longer than this is split hard. Extraction occasionally
# yields a whole article as one unpunctuated run, and one chunk holding 4,000
# characters would blow the context budget on its own.
MAX_SENTENCE_CHARS = TARGET_CHUNK_CHARS


@dataclass(frozen=True)
class Chunk:
    """One passage of one article. `ordinal` is its position, from 0."""

    ordinal: int
    text: str


def _hard_split(sentence: str) -> list[str]:
    """Break an over-long sentence on whitespace, never mid-word."""
    if len(sentence) <= MAX_SENTENCE_CHARS:
        return [sentence]
    parts: list[str] = []
    current = ""
    for word in sentence.split():
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > MAX_SENTENCE_CHARS:
            parts.append(current)
            current = word
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def chunk_article(text: str | None) -> list[Chunk]:
    """Split one article body into ordered, overlapping passages."""
    sentences: list[str] = []
    for sentence in split_sentences((text or "").strip()):
        sentences.extend(_hard_split(sentence))
    if not sentences:
        return []

    chunks: list[list[str]] = []
    current: list[str] = []
    length = 0

    for sentence in sentences:
        if current and length + len(sentence) > TARGET_CHUNK_CHARS:
            chunks.append(current)
            current = current[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []
            length = sum(len(s) for s in current)
        current.append(sentence)
        length += len(sentence)

    if current:
        # The tail can be a fragment. Merging it back beats storing a chunk that
        # is one clause long — but only if there is something to merge it into,
        # and only if the previous chunk is not itself already at budget.
        tail = " ".join(current)
        if (
            chunks
            and len(tail) < MIN_CHUNK_CHARS
            and sum(len(s) for s in chunks[-1]) + len(tail) <= TARGET_CHUNK_CHARS * 2
        ):
            chunks[-1].extend(current[OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else current)
        else:
            chunks.append(current)

    return [Chunk(ordinal=i, text=" ".join(parts)) for i, parts in enumerate(chunks)]


def embedded_text(title: str | None, chunk_text: str) -> str:
    """The exact string sent to the embedding model for a chunk.

    One definition, so the ingestion pass and any later re-measurement cannot
    disagree about it — the same reason src.analysis.embeddings.passage_text
    exists for the event vectors. Changing this invalidates every stored chunk
    vector, which is what `embedding_model` on the row is for.
    """
    title = (title or "").strip()
    return f"{title}\n\n{chunk_text}" if title else chunk_text

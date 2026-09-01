"""Turn evidence into the text the model reads, under a budget.

Two blocks, and the distinction between them is load-bearing. The **summary
block** is computed over the whole corpus by SQL — how many articles exist, how
they split by source and category, the mean polarity. The **passages block** is
what retrieval found. Aggregate questions ("איזה נושא הכי מסוקר?") are answered
outright by the first and not at all by the second, and the old assistant's most
visible bug was refusing exactly those questions because it read only the
article list as "the data".

Passages are numbered, and the model is required to cite by number. That is
what turns "the model said so" into a link a reader can open, and it is also
the cheapest hallucination check available: a citation that names a passage
which does not exist is detectable without a second model call.

Pure formatting — no database, no network — so what the model sees can be
tested by reading it.
"""

from __future__ import annotations

# A per-passage cap, so one long chunk cannot eat the whole budget. Chunks are
# built to ~700 characters (src/rag/chunking.py); this only bites on a chunk
# that merged a short tail.
MAX_PASSAGE_CHARS = 900

# The evidence budget, in characters. Around 3-4k tokens of Hebrew, which on
# gpt-4o-mini is a fraction of a cent per question and leaves the model plenty
# of room to answer. Enforced here rather than trusted to the chunk count,
# because the cap is what makes the cost per question predictable.
MAX_CONTEXT_CHARS = 7000

# Mirrors frontend/src/lib/format.ts SOURCE_LABELS. Included so a question
# phrased with the Hebrew display name ("הארץ") reaches the internal source
# code ("haaretz") without the model guessing at the mapping.
SOURCE_LABELS: dict[str, str] = {
    "ynet": "ynet",
    "haaretz": "הארץ",
    "mako": "mako",
    "news12": "חדשות 12",
    "reshet13": "רשת 13",
    "channel14": "ערוץ 14",
}


def source_display(source: str) -> str:
    label = SOURCE_LABELS.get(source)
    return f"{source} ({label})" if label and label != source else source


def format_stats(stats: dict) -> str:
    """The corpus-wide numbers, as prose the model can quote directly."""
    lines = [
        f"סה\"כ כתבות במסד הנתונים: {stats['total_articles']}",
        f"סה\"כ תגובות שנאספו: {stats['total_comments']}",
    ]
    if stats.get("avg_audience_mean") is not None:
        lines.append(f"קיטוב ממוצע כללי בתגובות: {stats['avg_audience_mean']:.4f}")
    if stats.get("by_source"):
        lines.append(
            "התפלגות לפי מקור: "
            + ", ".join(
                f"{source_display(row['source'])}: {row['article_count']} כתבות"
                + (
                    f" (קיטוב ממוצע {row['avg_audience_mean']:.4f})"
                    if row.get("avg_audience_mean") is not None
                    else ""
                )
                for row in stats["by_source"]
            )
        )
    if stats.get("by_category"):
        lines.append(
            "התפלגות לפי קטגוריה: "
            + ", ".join(
                f"{row['category']}: {row['article_count']} כתבות"
                for row in stats["by_category"]
            )
        )
    return "\n".join(lines)


def _passage_header(index: int, chunk: dict) -> str:
    polarity = (
        f"{chunk['audience_mean']:.4f}"
        if chunk.get("audience_mean") is not None
        else "אין נתון"
    )
    return (
        f"[{index}] מקור: {source_display(chunk['source'])} | "
        f"קטגוריה: {chunk.get('primary_category') or 'לא מסווג'} | "
        f"תאריך: {chunk['first_seen_at']} | "
        f"תגובות: {chunk.get('num_comments') or 0} | "
        f"קיטוב בתגובות: {polarity}\n"
        f"    כותרת: {chunk.get('title') or '(ללא כותרת)'}"
    )


def format_passages(chunks: list[dict]) -> tuple[str, list[dict]]:
    """Render retrieved chunks as numbered passages.

    Returns the text and the chunks that actually fit, in the same order — so
    citation [3] always refers to the third element of the returned list, and a
    passage dropped by the budget can never be cited.
    """
    if not chunks:
        return "לא נמצאו קטעים רלוונטיים במסד הנתונים לשאלה זו.", []

    blocks: list[str] = []
    included: list[dict] = []
    used = 0
    for chunk in chunks:
        text = chunk["text"][:MAX_PASSAGE_CHARS]
        block = f"{_passage_header(len(included) + 1, chunk)}\n    קטע: {text}"
        if used + len(block) > MAX_CONTEXT_CHARS and included:
            break
        blocks.append(block)
        included.append(chunk)
        used += len(block)
    return "\n\n".join(blocks), included


def build_user_message(*, question: str, stats: dict, chunks: list[dict]) -> tuple[str, list[dict]]:
    """Assemble everything the model is allowed to use, plus the question.

    Returns the message and the passages it contains, so the caller can resolve
    the citations the model comes back with.
    """
    passages, included = format_passages(chunks)
    message = (
        f"נתוני סיכום כלליים מהמערכת (על כל הכתבות, לא מסונן):\n{format_stats(stats)}\n\n"
        f"קטעים רלוונטיים שאותרו במסד הנתונים:\n{passages}\n\n"
        f"שאלת המשתמש:\n{question}"
    )
    return message, included

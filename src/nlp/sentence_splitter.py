"""Deterministic rule-based sentence splitting."""

from __future__ import annotations

import re

SENTENCE_END_PATTERN = re.compile(r"(?<=[.!?…])\s+")
ABBREVIATION_PATTERN = re.compile(
    r"\b(?:dr|mr|mrs|ms|prof|etc|e\.g|i\.e)\.\s+",
    re.IGNORECASE,
)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences while preserving order."""
    if not text.strip():
        return []

    protected = ABBREVIATION_PATTERN.sub(
        lambda match: match.group(0).replace(". ", "<DOT> "),
        text,
    )
    parts = SENTENCE_END_PATTERN.split(protected)
    sentences: list[str] = []
    for part in parts:
        restored = part.replace("<DOT> ", ". ").strip()
        if restored:
            sentences.append(restored)
    return sentences

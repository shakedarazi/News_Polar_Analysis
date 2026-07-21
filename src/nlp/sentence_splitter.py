"""Deterministic rule-based sentence splitting."""

from __future__ import annotations

import re

from src.nlp.tokenize import tokenize

MAX_WINDOW_TOKENS = 60

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


def sentence_windows(text: str, max_tokens: int = MAX_WINDOW_TOKENS) -> list[str]:
    """Sentence-based windows, chunked at `max_tokens` per the article-window RFC."""
    windows: list[str] = []
    for sentence in split_sentences(text):
        tokens = tokenize(sentence)
        if len(tokens) <= max_tokens:
            windows.append(sentence)
            continue
        for start in range(0, len(tokens), max_tokens):
            windows.append(" ".join(tokens[start : start + max_tokens]))
    return windows

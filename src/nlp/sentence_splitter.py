"""Rule-based sentence splitting."""

from __future__ import annotations

import re

from src.nlp.tokenize import tokenize

_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s+")
_ABBREV_PROTECT = (
    ("ד\"ר", "ד__dr__"),
    ("פרופ'", "פרופ__"),
    ("לדוג'", "לדוג__"),
    ("כו'", "כו__"),
    ("או\"ם", "או__m__"),
    ("צה\"ל", "צה__l__"),
    ("ש\"ס", "ש__s__"),
)


def split_sentences(text: str) -> list[str]:
    if not text.strip():
        return []
    protected = text
    for original, placeholder in _ABBREV_PROTECT:
        protected = protected.replace(original, placeholder)
    parts = _SENTENCE_END_RE.split(protected.strip())
    sentences: list[str] = []
    for part in parts:
        restored = part
        for original, placeholder in _ABBREV_PROTECT:
            restored = restored.replace(placeholder, original)
        restored = restored.strip()
        if restored:
            sentences.append(restored)
    return sentences


def sentence_windows(text: str, *, max_tokens: int = 60) -> list[str]:
    """Split text into sentence windows, chunking long sentences."""
    windows: list[str] = []
    for sentence in split_sentences(text):
        tokens = tokenize(sentence, normalized=True)
        if len(tokens) <= max_tokens:
            windows.append(sentence)
            continue
        for start in range(0, len(tokens), max_tokens):
            windows.append(" ".join(tokens[start : start + max_tokens]))
    return windows

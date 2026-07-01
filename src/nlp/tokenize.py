"""Whitespace-based tokenization."""

from __future__ import annotations

from src.nlp.normalize import normalize_text


def tokenize(text: str, *, normalized: bool = False) -> list[str]:
    value = text if normalized else normalize_text(text)
    if not value:
        return []
    return value.split()

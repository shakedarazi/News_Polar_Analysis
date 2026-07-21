"""Whitespace-based tokenization."""

from __future__ import annotations


def tokenize(text: str, normalized: bool = True) -> list[str]:
    """Split normalized text into tokens on whitespace.

    `normalized` is accepted for API compatibility with callers that
    normalize text before tokenizing (tokenization itself is a no-op
    whitespace split either way).
    """
    if not text:
        return []
    return text.split()

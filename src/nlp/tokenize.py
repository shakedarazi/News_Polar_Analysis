"""Whitespace-based tokenization."""

from __future__ import annotations


def tokenize(text: str) -> list[str]:
    """Split normalized text into tokens on whitespace."""
    if not text:
        return []
    return text.split()

"""Text normalization for articles and comments."""

from __future__ import annotations

import re
import unicodedata

URL_PATTERN = re.compile(r"https?://\S+")
NON_LINGUISTIC_PATTERN = re.compile(r"[^\w\s\u0590-\u05FF'-]", re.UNICODE)
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Apply deterministic normalization without semantic changes."""
    normalized = text
    normalized = URL_PATTERN.sub(" ", normalized)
    normalized = "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = normalized.lower()
    normalized = NON_LINGUISTIC_PATTERN.sub(" ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized


# Alias used by src/analysis/* (lexicon-based polarity pipeline).
normalize_text = normalize

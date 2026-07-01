"""Text normalization for lexicon matching."""

from __future__ import annotations

import re
import unicodedata

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_NIQQUD_RE = re.compile(r"[\u0591-\u05C7]")
_NON_LINGUISTIC_RE = re.compile(r"[^\w\s\u0590-\u05FF'.!?…\-]", re.UNICODE)
_QUOTE_MAP = str.maketrans({
    "\u201c": '"',
    "\u201d": '"',
    "\u2018": "'",
    "\u2019": "'",
    "״": '"',
    "׳": "'",
    "–": "-",
    "—": "-",
})


def normalize_text(text: str) -> str:
    """Deterministic normalization before tokenization."""
    if not text:
        return ""
    value = text.translate(_QUOTE_MAP)
    value = _URL_RE.sub(" ", value)
    value = _NIQQUD_RE.sub("", value)
    value = value.lower()
    value = _NON_LINGUISTIC_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value

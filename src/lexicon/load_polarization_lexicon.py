"""Load the polarization lexicon from a single CSV source file."""

from __future__ import annotations

import csv
from pathlib import Path

from src.common.hashing import sha256_hex
from src.lexicon.expand_lexicon import Component, expand_lexicon

DEFAULT_LEXICON_PATH = Path("data/lexicon/polarization.csv")


def load_lexicon_rows(path: str | Path) -> list[dict[str, str]]:
    """Load lexicon rows from the canonical CSV."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_lexicon(path: str | Path = DEFAULT_LEXICON_PATH) -> dict[str, Component]:
    """Load lemma -> component mapping from the canonical CSV."""
    return {
        row["lemma"]: row["component"]
        for row in load_lexicon_rows(path)
        if row.get("lemma") and row.get("component")
    }


def load_expanded_lexicon(path: str | Path = DEFAULT_LEXICON_PATH) -> dict[str, Component]:
    """Expand canonical lemmas in memory for runtime matching."""
    return expand_lexicon(load_lexicon(path))


def lexicon_version_from_file(path: str | Path = DEFAULT_LEXICON_PATH) -> str:
    """Return a stable version id from lexicon file contents."""
    return sha256_hex(Path(path).read_text(encoding="utf-8"))


# Backward-compatible aliases
load_polarization_lexicon = load_lexicon

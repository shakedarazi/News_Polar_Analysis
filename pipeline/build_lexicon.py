#!/usr/bin/env python3
"""Build expanded lexicon JSON files from base word lists."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.lexicon.load_lexicon import save_expanded_lexicons


def main() -> int:
    article_version, comment_version = save_expanded_lexicons()
    print("Expanded lexicons written.")
    print(f"  article lexicon version: {article_version[:16]}...")
    print(f"  comment lexicon version: {comment_version[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

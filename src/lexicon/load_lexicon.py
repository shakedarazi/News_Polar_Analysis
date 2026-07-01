"""Lexicon loading and offline prefix expansion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEXICON_BASE_DIR = ROOT / "data" / "lexicon_base"
COMMENT_LEXICON_BASE = ROOT / "data" / "comment_lexicon_base" / "polar_words.txt"
LEXICON_EXPANDED_DIR = ROOT / "data" / "lexicon_expanded"
COMMENT_LEXICON_EXPANDED_DIR = ROOT / "data" / "comment_lexicon_expanded"

PREFIXES = ("ה", "ו", "ב", "ל", "מ", "כ", "ש")
TWO_PREFIX_WHITELIST = ("וה", "וב", "ול", "ומ", "וכ", "וש")


def _read_word_file(path: Path) -> list[str]:
    words: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        words.append(line)
    return words


def _expand_word(word: str) -> set[str]:
    forms = {word}
    if len(word) < 3:
        return forms
    for prefix in PREFIXES:
        forms.add(prefix + word)
    for combo in TWO_PREFIX_WHITELIST:
        forms.add(combo + word)
    return forms


def build_article_lexicon() -> dict[str, int]:
    """Return token -> category index (1..7)."""
    mapping: dict[str, int] = {}
    for index in range(1, 8):
        path = LEXICON_BASE_DIR / f"category{index}.txt"
        if not path.is_file():
            continue
        for word in _read_word_file(path):
            for form in _expand_word(word):
                mapping.setdefault(form, index)
    return mapping


def build_comment_lexicon() -> set[str]:
    if not COMMENT_LEXICON_BASE.is_file():
        return set()
    words: set[str] = set()
    for word in _read_word_file(COMMENT_LEXICON_BASE):
        words.update(_expand_word(word))
    return words


def lexicon_version(mapping: dict | set) -> str:
    payload = json.dumps(mapping, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def save_expanded_lexicons() -> tuple[str, str]:
    LEXICON_EXPANDED_DIR.mkdir(parents=True, exist_ok=True)
    COMMENT_LEXICON_EXPANDED_DIR.mkdir(parents=True, exist_ok=True)

    article_map = build_article_lexicon()
    comment_set = sorted(build_comment_lexicon())

    article_version = lexicon_version(article_map)
    comment_version = lexicon_version(comment_set)

    (LEXICON_EXPANDED_DIR / "lexicon_expanded.json").write_text(
        json.dumps(article_map, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (LEXICON_EXPANDED_DIR / "lexicon_version.txt").write_text(article_version + "\n", encoding="utf-8")

    (COMMENT_LEXICON_EXPANDED_DIR / "comment_lexicon_expanded.json").write_text(
        json.dumps(comment_set, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (COMMENT_LEXICON_EXPANDED_DIR / "comment_lexicon_version.txt").write_text(
        comment_version + "\n",
        encoding="utf-8",
    )
    return article_version, comment_version


def load_article_lexicon() -> tuple[dict[str, int], str]:
    expanded_path = LEXICON_EXPANDED_DIR / "lexicon_expanded.json"
    version_path = LEXICON_EXPANDED_DIR / "lexicon_version.txt"
    if not expanded_path.is_file() or not version_path.is_file():
        save_expanded_lexicons()
    mapping = json.loads(expanded_path.read_text(encoding="utf-8"))
    version = version_path.read_text(encoding="utf-8").strip()
    return mapping, version


def load_comment_lexicon() -> tuple[set[str], str]:
    expanded_path = COMMENT_LEXICON_EXPANDED_DIR / "comment_lexicon_expanded.json"
    version_path = COMMENT_LEXICON_EXPANDED_DIR / "comment_lexicon_version.txt"
    if not expanded_path.is_file() or not version_path.is_file():
        save_expanded_lexicons()
    words = set(json.loads(expanded_path.read_text(encoding="utf-8")))
    version = version_path.read_text(encoding="utf-8").strip()
    return words, version

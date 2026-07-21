"""Deterministic token matching against an expanded polarization lexicon."""

from __future__ import annotations

from typing import Literal, Protocol

Component = Literal["issue", "affective"]

HEBREW_PREFIXES = frozenset("הובלמכש")
COMMON_SUFFIXES = ("יות", "ות", "ים", "ין", "ה", "י", "ו", "ת", "נו", "כם", "ן")
MIN_LOOKUP_LENGTH = 2


class TokenMatcher(Protocol):
    def match_tokens(
        self,
        tokens: list[str],
        lexicon_base: dict[str, str],
    ) -> dict[str, Component | None]:
        """Map each token to issue/affective or None if unmatched."""


class DeterministicLexiconMatcher:
    """Match tokens via expanded lexicon lookup and conservative Hebrew stripping."""

    def __init__(self, lexicon_expanded: dict[str, Component]) -> None:
        self.lexicon_expanded = lexicon_expanded

    def match_tokens(
        self,
        tokens: list[str],
        lexicon_base: dict[str, str] | None = None,
    ) -> dict[str, Component | None]:
        del lexicon_base
        unique_tokens = sorted(set(tokens))
        return {
            token: self._lookup(token)
            for token in unique_tokens
        }

    def _lookup(self, token: str) -> Component | None:
        for candidate in _candidate_forms(token):
            component = self.lexicon_expanded.get(candidate)
            if component is not None:
                return component
        return None


def _candidate_forms(token: str) -> list[str]:
    """Generate lookup candidates: exact, prefix-stripped, suffix-stripped."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(value: str) -> None:
        if len(value) < MIN_LOOKUP_LENGTH or value in seen:
            return
        seen.add(value)
        ordered.append(value)

    add(token)

    for prefix_form in _prefix_stripped(token):
        add(prefix_form)
        for suffix_form in _suffix_stripped(prefix_form):
            add(suffix_form)
            for inner_prefix in _prefix_stripped(suffix_form):
                add(inner_prefix)

    for suffix_form in _suffix_stripped(token):
        add(suffix_form)
        for prefix_form in _prefix_stripped(suffix_form):
            add(prefix_form)

    return ordered


def _prefix_stripped(token: str) -> list[str]:
    variants: list[str] = []
    current = token
    while len(current) >= MIN_LOOKUP_LENGTH + 1 and current[0] in HEBREW_PREFIXES:
        current = current[1:]
        variants.append(current)
    return variants


def _suffix_stripped(token: str) -> list[str]:
    variants: list[str] = []
    for suffix in COMMON_SUFFIXES:
        if len(token) <= len(suffix) + MIN_LOOKUP_LENGTH:
            continue
        if token.endswith(suffix):
            variants.append(token[: -len(suffix)])
    return variants

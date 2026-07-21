"""Offline expansion of base polarization lemmas into surface forms."""

from __future__ import annotations

from typing import Literal

Component = Literal["issue", "affective"]

SINGLE_PREFIXES = ("ה", "ו", "ב", "ל", "מ", "כ", "ש")
WHITELISTED_PREFIX_PAIRS = ("וה", "ול", "וב", "וש", "כש")
MIN_BASE_LENGTH = 3


def expand_lexicon(base: dict[str, Component]) -> dict[str, Component]:
    """Expand canonical lemmas with common Hebrew prefix variants."""
    expanded: dict[str, Component] = dict(base)

    for lemma, component in base.items():
        if len(lemma) < MIN_BASE_LENGTH:
            continue

        for prefix in SINGLE_PREFIXES:
            _insert_surface(expanded, prefix + lemma, component)

        for prefix in WHITELISTED_PREFIX_PAIRS:
            _insert_surface(expanded, prefix + lemma, component)

    return expanded


def _insert_surface(
    expanded: dict[str, Component],
    surface: str,
    component: Component,
) -> None:
    existing = expanded.get(surface)
    if existing is None:
        expanded[surface] = component
        return
    if existing != component:
        del expanded[surface]

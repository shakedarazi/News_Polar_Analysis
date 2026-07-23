"""Article window feature extraction."""

from __future__ import annotations

from dataclasses import dataclass

from src.nlp.normalize import normalize_text
from src.nlp.sentence_splitter import sentence_windows
from src.nlp.tokenize import tokenize


@dataclass
class WindowFeatures:
    sentence_idx: int
    window_len: int
    c1: int
    c2: int
    c3: int
    c4: int
    c5: int
    c6: int
    c7: int
    active: int
    dominance: float | None


def _counts_tuple(counts: list[int]) -> tuple[int, int, int, int, int, int, int]:
    return counts[0], counts[1], counts[2], counts[3], counts[4], counts[5], counts[6]


def extract_window_features(
    text: str,
    word_to_category: dict[str, int],
) -> list[WindowFeatures]:
    # Split on raw text first: normalization strips sentence-ending punctuation,
    # so normalizing before splitting collapses the article into one window.
    windows = sentence_windows(text)
    results: list[WindowFeatures] = []

    for sentence_idx, window_text in enumerate(windows):
        tokens = tokenize(normalize_text(window_text), normalized=True)
        counts = [0] * 7
        for token in tokens:
            category = word_to_category.get(token)
            if category is not None:
                counts[category - 1] += 1
        cat_words = sum(counts)
        active = sum(1 for count in counts if count > 0)
        dominance = (max(counts) / cat_words) if cat_words > 0 else None
        c1, c2, c3, c4, c5, c6, c7 = _counts_tuple(counts)
        results.append(
            WindowFeatures(
                sentence_idx=sentence_idx,
                window_len=len(tokens),
                c1=c1,
                c2=c2,
                c3=c3,
                c4=c4,
                c5=c5,
                c6=c6,
                c7=c7,
                active=active,
                dominance=dominance,
            )
        )
    return results

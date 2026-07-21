"""Comment-level polarity scoring."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.nlp.normalize import normalize_text
from src.nlp.tokenize import tokenize


@dataclass
class CommentFeatures:
    comment_id: str
    comment_len: int
    polar_count: int
    polar_ratio: float
    like_count: int
    dislike_count: int
    engagement_weight: float
    comment_score: float
    controversy: float


def engagement_weight(like_count: int, dislike_count: int = 0) -> float:
    return 1.0 + math.log(1.0 + like_count + dislike_count)


def controversy(like_count: int, dislike_count: int = 0) -> float:
    total = like_count + dislike_count
    if total <= 0:
        return 0.0
    p = like_count / total
    return 4.0 * p * (1.0 - p)


def score_comment(
    *,
    comment_id: str,
    text: str,
    polar_lexicon: set[str],
    like_count: int = 0,
    dislike_count: int = 0,
) -> CommentFeatures:
    normalized = normalize_text(text)
    tokens = tokenize(normalized, normalized=True)
    comment_len = len(tokens)
    polar_count = sum(1 for token in tokens if token in polar_lexicon)
    polar_ratio = polar_count / max(1, comment_len)
    weight = engagement_weight(like_count, dislike_count)
    return CommentFeatures(
        comment_id=comment_id,
        comment_len=comment_len,
        polar_count=polar_count,
        polar_ratio=polar_ratio,
        like_count=like_count,
        dislike_count=dislike_count,
        engagement_weight=weight,
        comment_score=polar_ratio,
        controversy=controversy(like_count, dislike_count),
    )

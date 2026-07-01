"""Article-level comment aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from src.analysis.comments_scoring import CommentFeatures


@dataclass
class ArticleCommentAgg:
    article_id: str
    num_comments: int
    audience_mean: float | None
    audience_p85: float | None
    controversy_mean: float | None
    controversy_p85: float | None
    sum_engagement_weight: float


def _weighted_mean(values: list[float], weights: list[float]) -> float | None:
    if not values or not weights or sum(weights) <= 0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)


def _weighted_quantile(
    values: list[float],
    weights: list[float],
    quantile: float = 0.85,
) -> float | None:
    if not values or not weights or sum(weights) <= 0:
        return None
    pairs = sorted(zip(values, weights), key=lambda item: item[0])
    target = quantile * sum(weights)
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= target:
            return value
    return pairs[-1][0]


def aggregate_comments(article_id: str, features: list[CommentFeatures]) -> ArticleCommentAgg:
    if not features:
        return ArticleCommentAgg(
            article_id=article_id,
            num_comments=0,
            audience_mean=None,
            audience_p85=None,
            controversy_mean=None,
            controversy_p85=None,
            sum_engagement_weight=0.0,
        )

    scores = [f.comment_score for f in features]
    controversies = [f.controversy for f in features]
    weights = [f.engagement_weight for f in features]
    total_weight = sum(weights)

    return ArticleCommentAgg(
        article_id=article_id,
        num_comments=len(features),
        audience_mean=_weighted_mean(scores, weights),
        audience_p85=_weighted_quantile(scores, weights),
        controversy_mean=_weighted_mean(controversies, weights),
        controversy_p85=_weighted_quantile(controversies, weights),
        sum_engagement_weight=total_weight,
    )

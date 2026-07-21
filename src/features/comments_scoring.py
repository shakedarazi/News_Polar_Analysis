"""Comment-level polarization scoring (Simchon-style, separate from article)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from src.common.hashing import comment_id_from_text
from src.features.article_windows import (
    Component,
    _compute_window_features,
    resolve_token_matches,
)
from src.lexicon.deterministic_matcher import TokenMatcher
from src.nlp.normalize import normalize
from src.nlp.tokenize import tokenize

CommentInput = dict[str, Any]


@dataclass(frozen=True)
class CommentPolarization:
    article_id: str
    comment_id: str
    comment_len: int
    issue_count: int
    affective_count: int
    polar_count: int
    issue_ratio: float | None
    affective_ratio: float | None
    polar_ratio: float | None
    like_count: int | None
    lexicon_version: str
    pipeline_version: str
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AudiencePolarization:
    """Article-level aggregation over comments (simple mean, not like-weighted)."""

    article_id: str
    num_comments: int
    audience_polar_mean: float | None
    audience_issue_mean: float | None
    audience_affective_mean: float | None
    lexicon_version: str
    pipeline_version: str
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommentsAnalysisResult:
    comments: list[CommentPolarization]
    token_matches: dict[str, Component | None]
    audience: AudiencePolarization

    def to_dict(self) -> dict[str, Any]:
        return {
            "comments": [comment.to_dict() for comment in self.comments],
            "token_matches": self.token_matches,
            "audience": self.audience.to_dict(),
        }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _comment_tokens(text: str) -> list[str]:
    return tokenize(normalize(text))


def _resolve_comment_id(
    article_id: str,
    comment: CommentInput,
    local_index: int,
) -> str:
    if comment_id := comment.get("comment_id"):
        return str(comment_id)
    return comment_id_from_text(article_id, str(comment.get("text", "")), local_index)


def aggregate_audience_polarization(
    comments: list[CommentPolarization],
    *,
    article_id: str,
    lexicon_version: str,
    pipeline_version: str,
    run_id: str,
) -> AudiencePolarization:
    """Mean of per-comment ratios across all comments with scorable text."""
    polar_values = [
        comment.polar_ratio
        for comment in comments
        if comment.polar_ratio is not None
    ]
    issue_values = [
        comment.issue_ratio
        for comment in comments
        if comment.issue_ratio is not None
    ]
    affective_values = [
        comment.affective_ratio
        for comment in comments
        if comment.affective_ratio is not None
    ]

    return AudiencePolarization(
        article_id=article_id,
        num_comments=len(comments),
        audience_polar_mean=_mean(polar_values),
        audience_issue_mean=_mean(issue_values),
        audience_affective_mean=_mean(affective_values),
        lexicon_version=lexicon_version,
        pipeline_version=pipeline_version,
        run_id=run_id,
    )


def compute_comments_analysis(
    article_id: str,
    comments: list[CommentInput],
    *,
    lexicon_version: str,
    pipeline_version: str,
    run_id: str,
    token_components: dict[str, Component] | None = None,
    lexicon_base: dict[str, str] | None = None,
    token_matcher: TokenMatcher | None = None,
) -> CommentsAnalysisResult:
    """Score each comment and aggregate audience means (separate from article)."""
    token_chunks: list[list[str]] = []
    comment_meta: list[tuple[str, int | None]] = []

    for local_index, comment in enumerate(comments):
        tokens = _comment_tokens(str(comment.get("text", "")))
        token_chunks.append(tokens)
        like_count = comment.get("like_count")
        comment_meta.append(
            (
                _resolve_comment_id(article_id, comment, local_index),
                int(like_count) if like_count is not None else None,
            )
        )

    token_matches = resolve_token_matches(
        token_chunks,
        token_components=token_components,
        lexicon_base=lexicon_base,
        token_matcher=token_matcher,
    )
    resolved_components = {
        token: component
        for token, component in token_matches.items()
        if component is not None
    }

    comment_features: list[CommentPolarization] = []
    for (comment_id, like_count), tokens in zip(comment_meta, token_chunks, strict=True):
        (
            issue_count,
            affective_count,
            polar_count,
            issue_ratio,
            affective_ratio,
            polar_ratio,
        ) = _compute_window_features(tokens, resolved_components)
        comment_features.append(
            CommentPolarization(
                article_id=article_id,
                comment_id=comment_id,
                comment_len=len(tokens),
                issue_count=issue_count,
                affective_count=affective_count,
                polar_count=polar_count,
                issue_ratio=issue_ratio,
                affective_ratio=affective_ratio,
                polar_ratio=polar_ratio,
                like_count=like_count,
                lexicon_version=lexicon_version,
                pipeline_version=pipeline_version,
                run_id=run_id,
            )
        )

    audience = aggregate_audience_polarization(
        comment_features,
        article_id=article_id,
        lexicon_version=lexicon_version,
        pipeline_version=pipeline_version,
        run_id=run_id,
    )
    return CommentsAnalysisResult(
        comments=comment_features,
        token_matches=token_matches,
        audience=audience,
    )

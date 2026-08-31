"""Two-axis polarization scoring over comment text.

The lexicon is the Hebrew adaptation of Simchon, Brady & Van Bavel (2022),
PNAS Nexus 1(1) pgac019, whose hierarchical clustering split into `issue`
(what the argument is about) and `affective` (hostility toward the other side).

This is a second reading of the same comments, not a better version of the
first. `src/analysis/comments_scoring.py` scores against a different list that
shares 15% of its expanded forms, and the two are never blended — see
docs/adr/0004. What is shared deliberately is the denominator: `comment_len`
is produced by the same normalize+tokenize pair, so a ratio here and a
`polar_ratio` there are the same kind of number over the same text.

Matching is a lookup against forms expanded once at build time, never runtime
stemming, which is the same rule the rest of the pipeline follows.

A comment with no text scores 0.0 on both axes, exactly as `polar_ratio` does.
The distinction between "not measured" and "measured as zero" is carried by the
database columns being NULL until this pass has run, not by the score itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.analysis.aggregation import _weighted_mean, _weighted_quantile
from src.lexicon.expand_lexicon import Component
from src.lexicon.load_polarization_lexicon import (
    lexicon_version_from_file,
    load_expanded_lexicon,
)
from src.nlp.normalize import normalize_text
from src.nlp.tokenize import tokenize


@dataclass
class CommentPolarization:
    comment_id: str
    comment_len: int
    issue_count: int
    affective_count: int
    polar_count: int
    issue_ratio: float
    affective_ratio: float


@dataclass
class ArticlePolarizationAgg:
    article_id: str
    num_comments: int
    audience_issue_mean: float | None
    audience_affective_mean: float | None
    audience_issue_p85: float | None
    audience_affective_p85: float | None


def load_polarization_lexicon_for_scoring() -> tuple[dict[str, Component], str]:
    """Expanded surface forms plus a version derived from the CSV's contents."""
    return load_expanded_lexicon(), lexicon_version_from_file()


def score_comment_polarization(
    *,
    comment_id: str,
    text: str,
    polarization_lexicon: dict[str, Component],
) -> CommentPolarization:
    tokens = tokenize(normalize_text(text), normalized=True)
    comment_len = len(tokens)

    issue_count = 0
    affective_count = 0
    for token in tokens:
        component = polarization_lexicon.get(token)
        if component == "issue":
            issue_count += 1
        elif component == "affective":
            affective_count += 1

    denominator = max(1, comment_len)
    return CommentPolarization(
        comment_id=comment_id,
        comment_len=comment_len,
        issue_count=issue_count,
        affective_count=affective_count,
        polar_count=issue_count + affective_count,
        issue_ratio=issue_count / denominator,
        affective_ratio=affective_count / denominator,
    )


def aggregate_polarization(
    article_id: str,
    weighted_features: list[tuple[CommentPolarization, float]],
) -> ArticlePolarizationAgg:
    """Like-weighted mean and p85 per axis.

    The weights are `engagement_weight` from the single-axis path, passed in
    rather than recomputed so both aggregates weight the same comment the same
    way. Without them the two readings would differ for a second reason on top
    of the lexicon, and neither difference could be attributed.
    """
    if not weighted_features:
        return ArticlePolarizationAgg(
            article_id=article_id,
            num_comments=0,
            audience_issue_mean=None,
            audience_affective_mean=None,
            audience_issue_p85=None,
            audience_affective_p85=None,
        )

    weights = [weight for _, weight in weighted_features]
    issue = [feature.issue_ratio for feature, _ in weighted_features]
    affective = [feature.affective_ratio for feature, _ in weighted_features]

    return ArticlePolarizationAgg(
        article_id=article_id,
        num_comments=len(weighted_features),
        audience_issue_mean=_weighted_mean(issue, weights),
        audience_affective_mean=_weighted_mean(affective, weights),
        audience_issue_p85=_weighted_quantile(issue, weights),
        audience_affective_p85=_weighted_quantile(affective, weights),
    )

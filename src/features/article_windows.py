"""Article window segmentation and polarization feature extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from src.lexicon.deterministic_matcher import TokenMatcher
from src.nlp.normalize import normalize
from src.nlp.sentence_splitter import split_sentences
from src.nlp.tokenize import tokenize

MAX_TOKENS_PER_WINDOW = 60
Component = Literal["issue", "affective"]


@dataclass(frozen=True)
class WindowFeature:
    article_id: str
    sentence_idx: int
    window_len: int
    issue_count: int
    affective_count: int
    polar_count: int
    issue_ratio: float | None
    affective_ratio: float | None
    polar_ratio: float | None
    lexicon_version: str
    pipeline_version: str
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArticleAnalysisResult:
    windows: list[WindowFeature]
    token_matches: dict[str, Component | None]
    article: ArticlePolarization

    def to_dict(self) -> dict[str, Any]:
        return {
            "windows": [window.to_dict() for window in self.windows],
            "token_matches": self.token_matches,
            "article": self.article.to_dict(),
        }


@dataclass(frozen=True)
class ArticlePolarization:
    article_id: str
    window_count: int
    total_tokens: int
    issue_count: int
    affective_count: int
    polar_count: int
    issue_ratio: float | None
    affective_ratio: float | None
    polar_ratio: float | None
    lexicon_version: str
    pipeline_version: str
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _chunk_tokens(tokens: list[str], chunk_size: int = MAX_TOKENS_PER_WINDOW) -> list[list[str]]:
    if len(tokens) <= chunk_size:
        return [tokens]
    return [
        tokens[index : index + chunk_size]
        for index in range(0, len(tokens), chunk_size)
    ]


def _ratio(count: int, total: int) -> float | None:
    if total == 0:
        return None
    return count / total


def _compute_window_features(
    tokens: list[str],
    token_components: dict[str, Component],
) -> tuple[int, int, int, float | None, float | None, float | None]:
    issue_count = 0
    affective_count = 0

    for token in tokens:
        component = token_components.get(token)
        if component == "issue":
            issue_count += 1
        elif component == "affective":
            affective_count += 1

    polar_count = issue_count + affective_count
    window_len = len(tokens)
    return (
        issue_count,
        affective_count,
        polar_count,
        _ratio(issue_count, window_len),
        _ratio(affective_count, window_len),
        _ratio(polar_count, window_len),
    )


def _ordered_unique_tokens(chunks: list[list[str]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for chunk in chunks:
        for token in chunk:
            if token not in seen:
                seen.add(token)
                ordered.append(token)
    return ordered


def resolve_token_matches(
    chunks: list[list[str]],
    *,
    token_components: dict[str, Component] | None,
    lexicon_base: dict[str, str] | None,
    token_matcher: TokenMatcher | None,
) -> dict[str, Component | None]:
    """Return a classification for every unique token (None if unmatched)."""
    if token_components is not None:
        unique_tokens = _ordered_unique_tokens(chunks)
        return {token: token_components.get(token) for token in unique_tokens}

    if token_matcher is None or lexicon_base is None:
        raise ValueError(
            "Provide either token_components or both lexicon_base and token_matcher"
        )

    unique_tokens = _ordered_unique_tokens(chunks)
    return token_matcher.match_tokens(unique_tokens, lexicon_base)


def _resolve_token_components(
    chunks: list[list[str]],
    *,
    token_components: dict[str, Component] | None,
    lexicon_base: dict[str, str] | None,
    token_matcher: TokenMatcher | None,
) -> dict[str, Component]:
    matches = resolve_token_matches(
        chunks,
        token_components=token_components,
        lexicon_base=lexicon_base,
        token_matcher=token_matcher,
    )
    return {
        token: component
        for token, component in matches.items()
        if component is not None
    }


def compute_article_analysis(
    article_id: str,
    text: str,
    *,
    lexicon_version: str,
    pipeline_version: str,
    run_id: str,
    token_components: dict[str, Component] | None = None,
    lexicon_base: dict[str, str] | None = None,
    token_matcher: TokenMatcher | None = None,
) -> ArticleAnalysisResult:
    """Analyze an article and return windows, token matches, and article scores."""
    chunk_list: list[list[str]] = []
    for sentence in split_sentences(text):
        sentence_tokens = tokenize(normalize(sentence))
        chunk_list.extend(_chunk_tokens(sentence_tokens))

    token_matches = resolve_token_matches(
        chunk_list,
        token_components=token_components,
        lexicon_base=lexicon_base,
        token_matcher=token_matcher,
    )
    resolved_components = {
        token: component
        for token, component in token_matches.items()
        if component is not None
    }

    windows: list[WindowFeature] = []
    for sentence_idx, chunk in enumerate(chunk_list):
        (
            issue_count,
            affective_count,
            polar_count,
            issue_ratio,
            affective_ratio,
            polar_ratio,
        ) = _compute_window_features(chunk, resolved_components)
        windows.append(
            WindowFeature(
                article_id=article_id,
                sentence_idx=sentence_idx,
                window_len=len(chunk),
                issue_count=issue_count,
                affective_count=affective_count,
                polar_count=polar_count,
                issue_ratio=issue_ratio,
                affective_ratio=affective_ratio,
                polar_ratio=polar_ratio,
                lexicon_version=lexicon_version,
                pipeline_version=pipeline_version,
                run_id=run_id,
            )
        )

    article = aggregate_article_polarization(
        windows,
        article_id=article_id,
        lexicon_version=lexicon_version,
        pipeline_version=pipeline_version,
        run_id=run_id,
    )
    return ArticleAnalysisResult(
        windows=windows,
        token_matches=token_matches,
        article=article,
    )


def compute_windows(
    article_id: str,
    text: str,
    *,
    lexicon_version: str,
    pipeline_version: str,
    run_id: str,
    token_components: dict[str, Component] | None = None,
    lexicon_base: dict[str, str] | None = None,
    token_matcher: TokenMatcher | None = None,
) -> list[WindowFeature]:
    """Split article text into windows and compute polarization features."""
    return compute_article_analysis(
        article_id,
        text,
        lexicon_version=lexicon_version,
        pipeline_version=pipeline_version,
        run_id=run_id,
        token_components=token_components,
        lexicon_base=lexicon_base,
        token_matcher=token_matcher,
    ).windows


def aggregate_article_polarization(
    windows: list[WindowFeature],
    *,
    article_id: str,
    lexicon_version: str,
    pipeline_version: str,
    run_id: str,
) -> ArticlePolarization:
    """Aggregate window counts into article-level polarization scores."""
    total_tokens = sum(window.window_len for window in windows)
    issue_count = sum(window.issue_count for window in windows)
    affective_count = sum(window.affective_count for window in windows)
    polar_count = issue_count + affective_count

    return ArticlePolarization(
        article_id=article_id,
        window_count=len(windows),
        total_tokens=total_tokens,
        issue_count=issue_count,
        affective_count=affective_count,
        polar_count=polar_count,
        issue_ratio=_ratio(issue_count, total_tokens),
        affective_ratio=_ratio(affective_count, total_tokens),
        polar_ratio=_ratio(polar_count, total_tokens),
        lexicon_version=lexicon_version,
        pipeline_version=pipeline_version,
        run_id=run_id,
    )

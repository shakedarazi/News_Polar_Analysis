"""Comment fetcher registry."""

from __future__ import annotations

from collections.abc import Callable

from src.crawling.comments import channel14, haaretz, mako, ynet
from src.crawling.comments.models import RawComment

CommentFetcher = Callable[[str], list[RawComment]]

FETCHERS: dict[str, CommentFetcher] = {
    "ynet": ynet.fetch_comments,
    "haaretz": haaretz.fetch_comments,
    "mako": mako.fetch_comments,
    "news12": mako.fetch_comments,
    "channel14": channel14.fetch_comments,
}

UNSUPPORTED_SOURCES = frozenset({"reshet13"})

ALL_COMMENT_SOURCES: list[str] = list(FETCHERS.keys())


def get_comment_fetcher(source: str) -> CommentFetcher | None:
    return FETCHERS.get(source.lower())


def supports_comments(source: str) -> bool:
    return source.lower() in FETCHERS

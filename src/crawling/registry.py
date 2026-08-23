"""Crawler registry for all supported news sources."""

from __future__ import annotations

import functools
from typing import Callable

from src.crawling.base import BaseCrawler
from src.crawling.sources.feed_dom import SOURCES, FeedDomCrawler
from src.crawling.sources.reshet13 import Reshet13Crawler
from src.crawling.sources.ynet import YnetCrawler

CRAWLERS: dict[str, Callable[[], BaseCrawler]] = {
    "ynet": YnetCrawler,
    "reshet13": Reshet13Crawler,
    **{
        name: functools.partial(FeedDomCrawler, name, cfg.feeds, cfg.dom_selectors, min_len=cfg.min_len)
        for name, cfg in SOURCES.items()
    },
}

ALL_SOURCES: list[str] = list(CRAWLERS.keys())


def get_crawler(source: str) -> BaseCrawler:
    key = source.lower()
    if key not in CRAWLERS:
        raise KeyError(f"Unknown source '{source}'. Available: {', '.join(ALL_SOURCES)}")
    return CRAWLERS[key]()

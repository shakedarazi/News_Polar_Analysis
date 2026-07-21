"""Crawler registry for all supported news sources."""

from __future__ import annotations

from src.crawling.base import BaseCrawler
from src.crawling.sources.channel14 import Channel14Crawler
from src.crawling.sources.haaretz import HaaretzCrawler
from src.crawling.sources.mako import MakoCrawler
from src.crawling.sources.news12 import News12Crawler
from src.crawling.sources.reshet13 import Reshet13Crawler
from src.crawling.sources.ynet import YnetCrawler

CRAWLERS: dict[str, type[BaseCrawler]] = {
    "ynet": YnetCrawler,
    "haaretz": HaaretzCrawler,
    "mako": MakoCrawler,
    "news12": News12Crawler,
    "reshet13": Reshet13Crawler,
    "channel14": Channel14Crawler,
}

ALL_SOURCES: list[str] = list(CRAWLERS.keys())


def get_crawler(source: str) -> BaseCrawler:
    key = source.lower()
    if key not in CRAWLERS:
        raise KeyError(f"Unknown source '{source}'. Available: {', '.join(ALL_SOURCES)}")
    return CRAWLERS[key]()

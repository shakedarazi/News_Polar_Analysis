"""Tests for crawler registry."""

from src.crawling.base import BaseCrawler
from src.crawling.registry import ALL_SOURCES, get_crawler
from src.crawling.sources.feed_dom import SOURCES


def test_all_sources_registered():
    assert len(ALL_SOURCES) == 6
    assert set(ALL_SOURCES) == {
        "ynet",
        "haaretz",
        "mako",
        "news12",
        "reshet13",
        "channel14",
    }


def test_get_crawler_returns_instance():
    for name in ALL_SOURCES:
        crawler = get_crawler(name)
        assert isinstance(crawler, BaseCrawler)
        assert crawler.source_name == name


def test_feed_dom_crawlers_wired_from_config():
    for name, cfg in SOURCES.items():
        crawler = get_crawler(name)
        assert crawler.feeds == cfg.feeds
        assert crawler.dom_selectors == cfg.dom_selectors
        assert crawler.min_len == cfg.min_len

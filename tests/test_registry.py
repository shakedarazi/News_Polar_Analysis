"""Tests for crawler registry."""

from src.crawling.registry import ALL_SOURCES, CRAWLERS, get_crawler


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
        assert crawler.source_name == name
        assert type(crawler) is CRAWLERS[name]

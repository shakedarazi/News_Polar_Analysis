"""Tests for RSS discovery helpers."""

from src.crawling.rss_utils import NO_LIMIT


def test_discover_unlimited_returns_all_entries(monkeypatch):
    from src.crawling import rss_utils

    def fake_fetch(_url: str) -> str:
        return """<?xml version="1.0"?>
        <rss><channel>
          <item><link>https://example.com/a</link></item>
          <item><link>https://example.com/b</link></item>
          <item><link>https://example.com/c</link></item>
        </channel></rss>"""

    monkeypatch.setattr(rss_utils, "fetch_feed_xml", fake_fetch)
    urls = rss_utils.discover_from_feeds(["http://fake"], NO_LIMIT)
    assert urls == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]


def test_discover_with_limit_stops_early(monkeypatch):
    from src.crawling import rss_utils

    def fake_fetch(_url: str) -> str:
        return """<?xml version="1.0"?>
        <rss><channel>
          <item><link>https://example.com/1</link></item>
          <item><link>https://example.com/2</link></item>
          <item><link>https://example.com/3</link></item>
        </channel></rss>"""

    monkeypatch.setattr(rss_utils, "fetch_feed_xml", fake_fetch)
    urls = rss_utils.discover_from_feeds(["http://fake"], 2)
    assert len(urls) == 2

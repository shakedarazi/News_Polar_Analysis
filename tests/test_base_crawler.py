"""Tests for the canonical per-source crawl loop on BaseCrawler."""

from src.crawling import base
from src.crawling.base import BaseCrawler


class FakeCrawler(BaseCrawler):
    source_name = "fake"

    def __init__(self, urls, extracted=None, fail_urls=None):
        self._urls = urls
        self._extracted = extracted or {}
        self._fail_urls = fail_urls or set()

    def discover_urls(self, limit):
        return self._urls

    def extract_article(self, url):
        if url in self._fail_urls:
            raise ValueError("boom")
        return self._extracted.get(url, {"title": "t", "text": "x" * 150})


def test_saves_new_articles_and_updates_known_ids(monkeypatch):
    saved = []
    monkeypatch.setattr(base, "save_article", lambda record: saved.append(record))

    crawler = FakeCrawler(["https://example.com/a", "https://example.com/b"])
    known_ids: set[str] = set()
    summary = crawler.crawl(run_id="run_1", delay_seconds=0, known_ids=known_ids, classify=False)

    assert summary.discovered == 2
    assert summary.saved == 2
    assert summary.skipped == 0
    assert summary.failed == 0
    assert len(saved) == 2
    assert len(known_ids) == 2


def test_skips_urls_already_in_known_ids(monkeypatch):
    from src.common.hashing import article_id_from_url

    saved = []
    monkeypatch.setattr(base, "save_article", lambda record: saved.append(record))

    url = "https://example.com/a"
    known_ids = {article_id_from_url(url)}
    crawler = FakeCrawler([url])
    summary = crawler.crawl(run_id="run_1", delay_seconds=0, known_ids=known_ids, classify=False)

    assert summary.skipped == 1
    assert summary.saved == 0
    assert saved == []


def test_one_article_failure_does_not_abort_the_source(monkeypatch):
    saved = []
    monkeypatch.setattr(base, "save_article", lambda record: saved.append(record))

    bad_url = "https://example.com/bad"
    good_url = "https://example.com/good"
    crawler = FakeCrawler([bad_url, good_url], fail_urls={bad_url})
    summary = crawler.crawl(run_id="run_1", delay_seconds=0, known_ids=set(), classify=False)

    assert summary.failed == 1
    assert summary.saved == 1
    assert len(saved) == 1

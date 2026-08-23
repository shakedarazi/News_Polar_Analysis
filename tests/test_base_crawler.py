"""Tests for the canonical per-source crawl loop on BaseCrawler."""

import logging

from src.crawling import base
from src.crawling.base import BaseCrawler, CrawlSummary, check_failure_rate_spike


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


def test_warns_when_failure_rate_of_attempted_articles_exceeds_threshold(caplog):
    # 4/6 attempted (saved+failed) failed = 67%, well over the 30% threshold,
    # with plenty of discovered volume.
    summary = CrawlSummary(source="ynet", discovered=10, saved=2, skipped=4, failed=4)

    with caplog.at_level(logging.WARNING, logger="ingestion.crawl"):
        check_failure_rate_spike(summary)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert "ynet" in caplog.records[0].message


def test_warns_even_when_skipped_dupes_would_dilute_the_rate_by_discovered_count(caplog):
    # Every attempted article failed (2/2), but most of the discovered batch
    # was already-known dupes - failed/discovered alone would hide this.
    summary = CrawlSummary(source="mako", discovered=20, saved=0, skipped=18, failed=2)

    with caplog.at_level(logging.WARNING, logger="ingestion.crawl"):
        check_failure_rate_spike(summary)

    assert len(caplog.records) == 1


def test_no_warning_when_volume_is_too_small(caplog):
    # 3/4 attempted failed = 75% failure rate, but only 4 articles discovered (< 5).
    summary = CrawlSummary(source="mako", discovered=4, saved=1, skipped=0, failed=3)

    with caplog.at_level(logging.WARNING, logger="ingestion.crawl"):
        check_failure_rate_spike(summary)

    assert caplog.records == []


def test_no_warning_when_failure_rate_at_or_below_threshold(caplog):
    # Exactly 30% of attempted articles failed with plenty of volume - not "exceeds".
    summary = CrawlSummary(source="haaretz", discovered=10, saved=7, skipped=0, failed=3)

    with caplog.at_level(logging.WARNING, logger="ingestion.crawl"):
        check_failure_rate_spike(summary)

    assert caplog.records == []


def test_no_warning_when_nothing_was_attempted(caplog):
    # All discovered articles were already-known dupes - nothing to alert on.
    summary = CrawlSummary(source="news12", discovered=10, saved=0, skipped=10, failed=0)

    with caplog.at_level(logging.WARNING, logger="ingestion.crawl"):
        check_failure_rate_spike(summary)

    assert caplog.records == []

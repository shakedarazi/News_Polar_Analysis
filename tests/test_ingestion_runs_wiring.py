"""Confirms pipeline.crawl.run_all_sources writes one ingestion_runs row per
source via src.db.ingestion_runs.record_ingestion_run, using a mocked writer
rather than a real database.
"""

from pipeline import crawl
from src.crawling.base import BaseCrawler, CrawlSummary


class _FakeCrawler(BaseCrawler):
    source_name = "fake"

    def __init__(self, summary=None, error=None):
        self._summary = summary
        self._error = error

    def discover_urls(self, limit):
        return []

    def extract_article(self, url):
        return {"title": "t", "text": "x"}

    def crawl(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._summary


def test_records_one_row_per_source_with_correct_counts(monkeypatch):
    crawlers = {
        "ynet": _FakeCrawler(CrawlSummary(source="ynet", discovered=5, saved=3, skipped=1, failed=1)),
        "haaretz": _FakeCrawler(CrawlSummary(source="haaretz", discovered=2, saved=2, skipped=0, failed=0)),
    }
    monkeypatch.setattr(crawl, "get_crawler", lambda name: crawlers[name])

    recorded = []
    monkeypatch.setattr(
        crawl,
        "record_ingestion_run",
        lambda **kwargs: recorded.append(kwargs),
    )

    result = crawl.run_all_sources(
        ["ynet", "haaretz"],
        run_id="run_1",
        limit=10,
        delay_seconds=0,
        known_ids=set(),
        classify=False,
    )

    assert result.total_saved == 5
    assert result.total_skipped == 1
    assert result.total_failed == 1
    assert result.sources_crashed == []

    assert len(recorded) == 2
    assert recorded[0]["source"] == "ynet"
    assert recorded[0]["saved"] == 3
    assert recorded[0]["skipped"] == 1
    assert recorded[0]["failed"] == 1
    assert recorded[0].get("crashed", False) is False
    assert recorded[1]["source"] == "haaretz"
    assert recorded[1]["saved"] == 2
    assert recorded[1]["skipped"] == 0
    assert recorded[1]["failed"] == 0
    assert recorded[1].get("crashed", False) is False


def test_crashed_source_still_records_a_row(monkeypatch):
    crawlers = {
        "mako": _FakeCrawler(error=RuntimeError("feed timeout")),
    }
    monkeypatch.setattr(crawl, "get_crawler", lambda name: crawlers[name])

    recorded = []
    monkeypatch.setattr(
        crawl,
        "record_ingestion_run",
        lambda **kwargs: recorded.append(kwargs),
    )

    result = crawl.run_all_sources(
        ["mako"],
        run_id="run_1",
        limit=10,
        delay_seconds=0,
        known_ids=set(),
        classify=False,
    )

    assert result.total_saved == 0
    assert result.sources_crashed == ["mako"]
    assert len(recorded) == 1
    assert recorded[0]["source"] == "mako"
    assert recorded[0]["crashed"] is True
    assert recorded[0]["error_message"] == "feed timeout"

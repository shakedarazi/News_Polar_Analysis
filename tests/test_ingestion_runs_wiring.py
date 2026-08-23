"""Confirms pipeline.crawl.run_all_sources writes one ingestion_runs row per
source via src.db.ingestion_runs.record_ingestion_run, using a mocked writer
rather than a real database.

Sources now run concurrently (one worker per source), so assertions key off
`source` rather than list position - completion order across workers isn't
guaranteed.
"""

import threading

from pipeline import crawl
from src.crawling.base import BaseCrawler, CrawlSummary
from src.crawling.known_ids import KnownIds


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
    record_lock = threading.Lock()

    def fake_record(**kwargs):
        with record_lock:
            recorded.append(kwargs)

    monkeypatch.setattr(crawl, "record_ingestion_run", fake_record)

    result = crawl.run_all_sources(
        ["ynet", "haaretz"],
        run_id="run_1",
        limit=10,
        delay_seconds=0,
        known_ids=KnownIds(),
    )

    assert result.total_saved == 5
    assert result.total_skipped == 1
    assert result.total_failed == 1
    assert result.sources_crashed == []

    by_source = {row["source"]: row for row in recorded}
    assert set(by_source) == {"ynet", "haaretz"}
    assert by_source["ynet"]["saved"] == 3
    assert by_source["ynet"]["skipped"] == 1
    assert by_source["ynet"]["failed"] == 1
    assert by_source["ynet"].get("crashed", False) is False
    assert by_source["haaretz"]["saved"] == 2
    assert by_source["haaretz"]["skipped"] == 0
    assert by_source["haaretz"]["failed"] == 0
    assert by_source["haaretz"].get("crashed", False) is False


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
        known_ids=KnownIds(),
    )

    assert result.total_saved == 0
    assert result.sources_crashed == ["mako"]
    assert len(recorded) == 1
    assert recorded[0]["source"] == "mako"
    assert recorded[0]["crashed"] is True
    assert recorded[0]["error_message"] == "feed timeout"


def test_one_source_crashing_does_not_stop_others_running_concurrently(monkeypatch):
    """A barrier forces all three workers' crawl() calls to be genuinely
    in flight at the same moment, rather than hoping thread scheduling
    happens to overlap them - the crashing source must not block or abort
    the other two, which are still mid-crawl when it raises.
    """
    start = threading.Barrier(3)

    class _BarrieredCrawler(BaseCrawler):
        def __init__(self, source_name, summary=None, error=None):
            self.source_name = source_name
            self._summary = summary
            self._error = error

        def discover_urls(self, limit):
            return []

        def extract_article(self, url):
            return {"title": "t", "text": "x"}

        def crawl(self, **kwargs):
            start.wait(timeout=2)
            if self._error is not None:
                raise self._error
            return self._summary

    crawlers = {
        "ynet": _BarrieredCrawler("ynet", CrawlSummary(source="ynet", discovered=1, saved=1, skipped=0, failed=0)),
        "mako": _BarrieredCrawler("mako", error=RuntimeError("feed timeout")),
        "haaretz": _BarrieredCrawler(
            "haaretz", CrawlSummary(source="haaretz", discovered=1, saved=1, skipped=0, failed=0)
        ),
    }
    monkeypatch.setattr(crawl, "get_crawler", lambda name: crawlers[name])

    recorded = []
    record_lock = threading.Lock()

    def fake_record(**kwargs):
        with record_lock:
            recorded.append(kwargs)

    monkeypatch.setattr(crawl, "record_ingestion_run", fake_record)

    result = crawl.run_all_sources(
        ["ynet", "mako", "haaretz"],
        run_id="run_1",
        limit=10,
        delay_seconds=0,
        known_ids=KnownIds(),
    )

    assert result.sources_crashed == ["mako"]
    assert result.total_saved == 2
    assert {row["source"] for row in recorded} == {"ynet", "mako", "haaretz"}

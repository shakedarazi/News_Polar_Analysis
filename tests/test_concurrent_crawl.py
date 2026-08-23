"""Confirms two source workers sharing one KnownIds instance never both save
the same article, exercised via BaseCrawler.crawl() itself (not just the
KnownIds unit) with a forced, controlled overlap rather than hoping real
thread scheduling produces the race.
"""

import threading

from src.crawling import base
from src.crawling.base import BaseCrawler
from src.crawling.known_ids import KnownIds


class _BarrieredCrawler(BaseCrawler):
    """Discovers the same URL as its sibling worker and uses a barrier so
    both workers' check_and_add calls are forced to be genuinely in flight
    at the same moment - the exact interleaving a check-then-act race would
    need to actually corrupt state.
    """

    def __init__(self, source_name, url, start_barrier):
        self.source_name = source_name
        self._url = url
        self._start_barrier = start_barrier

    def discover_urls(self, limit):
        self._start_barrier.wait(timeout=2)
        return [self._url]

    def extract_article(self, url):
        return {"title": "t", "text": "x" * 150}


def test_two_workers_sharing_known_ids_never_both_save_the_same_article(monkeypatch):
    saved = []
    save_lock = threading.Lock()

    def fake_save(record):
        with save_lock:
            saved.append(record)

    monkeypatch.setattr(base, "save_article", fake_save)

    url = "https://example.com/shared"
    known_ids = KnownIds()
    start = threading.Barrier(2)

    crawler_a = _BarrieredCrawler("a", url, start)
    crawler_b = _BarrieredCrawler("b", url, start)
    summaries = {}

    def run(key, crawler):
        summaries[key] = crawler.crawl(run_id="run_1", delay_seconds=0, known_ids=known_ids)

    t1 = threading.Thread(target=run, args=("a", crawler_a))
    t2 = threading.Thread(target=run, args=("b", crawler_b))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert summaries["a"].saved + summaries["b"].saved == 1
    assert summaries["a"].skipped + summaries["b"].skipped == 1
    assert len(saved) == 1
    assert len(known_ids) == 1

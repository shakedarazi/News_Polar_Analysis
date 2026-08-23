"""Base crawler interface."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.common.hashing import article_id_from_url
from src.crawling.extract_article import build_article_record
from src.db.articles import load_known_ids, save_article

logger = logging.getLogger("ingestion.crawl")


@dataclass
class CrawlSummary:
    source: str
    discovered: int = 0
    saved: int = 0
    skipped: int = 0
    failed: int = 0


# Below this discovery count, a single bad article inflates the failure rate
# past the threshold on noise alone (e.g. tiny RSS batches) - not worth paging on.
MIN_DISCOVERED_FOR_FAILURE_ALERT = 5
FAILURE_RATE_ALERT_THRESHOLD = 0.3


def check_failure_rate_spike(summary: CrawlSummary) -> None:
    """Log a WARNING if this source's article failure rate spiked this run.

    The rate is failed / attempted (saved + failed) - skipped duplicates were
    never attempted, so including them would dilute a real failure spike on
    runs with a lot of already-known articles. The volume gate below is on
    `discovered` per the spec, since that's what makes a run "small enough
    to be noise" regardless of how many of those turned out to be dupes.
    """
    if summary.discovered < MIN_DISCOVERED_FOR_FAILURE_ALERT:
        return
    attempted = summary.saved + summary.failed
    if attempted == 0:
        return
    failure_rate = summary.failed / attempted
    if failure_rate > FAILURE_RATE_ALERT_THRESHOLD:
        logger.warning(
            "%s: failure rate spike - %d/%d attempted articles failed (%.0f%%)",
            summary.source, summary.failed, attempted, failure_rate * 100,
        )


class BaseCrawler(ABC):
    source_name: str

    @abstractmethod
    def discover_urls(self, limit: int) -> list[str]:
        """Return article URLs to fetch."""

    @abstractmethod
    def extract_article(self, url: str) -> dict[str, str]:
        """Return dict with title, text, and url."""

    def crawl(
        self,
        *,
        limit: int = 10,
        run_id: str,
        delay_seconds: float = 2.0,
        known_ids: set[str] | None = None,
    ) -> CrawlSummary:
        known_ids = known_ids if known_ids is not None else load_known_ids()

        urls = self.discover_urls(limit)
        summary = CrawlSummary(source=self.source_name, discovered=len(urls))
        logger.info("%s: %d articles found (RSS/feed discovery)", self.source_name, len(urls))

        for index, url in enumerate(urls, start=1):
            aid = article_id_from_url(url)
            if aid in known_ids:
                logger.debug("[%d/%d] SKIP (duplicate): %s", index, len(urls), url)
                summary.skipped += 1
                continue

            logger.debug("[%d/%d] Fetching: %s", index, len(urls), url)
            try:
                article = self.extract_article(url)
                record = build_article_record(
                    source=self.source_name,
                    title=article["title"],
                    text=article["text"],
                    url=url,
                    run_id=run_id,
                )
                save_article(record)
                logger.info(
                    "  OK: %s (%d chars -> db:%s...)",
                    article["title"][:70],
                    len(article["text"]),
                    record["article_id"][:16],
                )
                summary.saved += 1
                known_ids.add(aid)
            except Exception as exc:
                logger.error("  FAILED to fetch/save %s: %s", url, exc, exc_info=True)
                summary.failed += 1

            time.sleep(delay_seconds)

        logger.info(
            "%s: new articles inserted=%d, duplicates skipped=%d, failed=%d",
            self.source_name, summary.saved, summary.skipped, summary.failed,
        )
        check_failure_rate_spike(summary)
        return summary

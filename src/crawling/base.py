"""Base crawler interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.common.hashing import article_id_from_url
from src.crawling.extract_article import build_article_record
from src.db.articles import load_known_ids, save_article
from src.db.classification import maybe_classify_after_save


@dataclass
class CrawlResult:
    article_id: str
    title: str
    skipped: bool = False


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
        classify: bool = True,
    ) -> list[CrawlResult]:
        import time

        known_ids = known_ids if known_ids is not None else load_known_ids()
        results: list[CrawlResult] = []
        urls = self.discover_urls(limit)

        for index, url in enumerate(urls, start=1):
            aid = article_id_from_url(url)
            if aid in known_ids:
                results.append(
                    CrawlResult(
                        article_id=aid,
                        title="",
                        skipped=True,
                    )
                )
                continue

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
                maybe_classify_after_save(record, enabled=classify)
                results.append(
                    CrawlResult(
                        article_id=aid,
                        title=article["title"],
                    )
                )
                known_ids.add(aid)
            except Exception as exc:
                print(f"  [{index}/{len(urls)}] FAILED {url}: {exc}")
                continue

            if index < len(urls):
                time.sleep(delay_seconds)

        return results

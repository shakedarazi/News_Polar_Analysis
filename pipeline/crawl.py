#!/usr/bin/env python3
"""Crawl articles from Israeli news sources into PostgreSQL."""

from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.crawling.base import CrawlSummary
from src.crawling.known_ids import KnownIds
from src.crawling.registry import ALL_SOURCES, get_crawler
from src.crawling.rss_utils import NO_LIMIT
from src.db.articles import load_known_ids
from src.db.config import get_database_url, require_database_url
from src.db.ingestion_runs import record_ingestion_run

# Child of the "ingestion" logger configured in src/scheduler/ingestion_scheduler.py
# (rotating file + console handlers attached there). When this module is run
# directly as a CLI (not via the scheduler), __main__ below attaches its own
# basicConfig so output still shows up in the terminal as before.
logger = logging.getLogger("ingestion.crawl")


@dataclass
class RunAllSourcesResult:
    total_saved: int
    total_skipped: int
    total_failed: int
    sources_crashed: list[str]


def _crawl_one_source(
    source: str,
    *,
    run_id: str,
    limit: int,
    delay_seconds: float,
    known_ids: KnownIds,
) -> tuple[str, CrawlSummary | None, Exception | None]:
    """Crawl a single source and record its own ingestion_runs row.

    Runs inside a worker thread when called via run_all_sources' pool, so
    the ingestion_runs write happens from the worker that produced it.
    """
    started_at = datetime.now(timezone.utc)
    # Fault tolerance: a single source raising (feed timeout, parser bug,
    # site markup change, ...) must never stop the remaining sources —
    # this loop previously had no protection here, so one bad source
    # silently killed the whole scheduled run.
    try:
        summary = get_crawler(source).crawl(
            limit=limit,
            run_id=run_id,
            delay_seconds=delay_seconds,
            known_ids=known_ids,
        )
    except Exception as exc:
        logger.error("Source %s crashed and was skipped: %s", source, exc, exc_info=True)
        record_ingestion_run(
            run_id=run_id,
            source=source,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            crashed=True,
            error_message=str(exc),
        )
        return source, None, exc

    record_ingestion_run(
        run_id=run_id,
        source=source,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        saved=summary.saved,
        skipped=summary.skipped,
        failed=summary.failed,
    )
    return source, summary, None


def run_all_sources(
    sources: list[str],
    *,
    run_id: str,
    limit: int,
    delay_seconds: float,
    known_ids: KnownIds,
) -> RunAllSourcesResult:
    """Crawl all sources concurrently (one worker per source), recording one
    ingestion_runs row per source. Article-by-article fetching stays
    sequential within each source - only the sources themselves overlap.
    """
    total_saved = total_skipped = total_failed = 0
    sources_crashed: list[str] = []

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futures = [
            pool.submit(
                _crawl_one_source,
                source,
                run_id=run_id,
                limit=limit,
                delay_seconds=delay_seconds,
                known_ids=known_ids,
            )
            for source in sources
        ]
        for future in futures:
            source, summary, exc = future.result()
            if exc is not None:
                sources_crashed.append(source)
                continue
            total_saved += summary.saved
            total_skipped += summary.skipped
            total_failed += summary.failed

    return RunAllSourcesResult(total_saved, total_skipped, total_failed, sources_crashed)


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl news articles to PostgreSQL")
    parser.add_argument(
        "--source",
        default="all",
        help=f"Source name or 'all'. Options: {', '.join(ALL_SOURCES)}, all",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=NO_LIMIT,
        help="Max articles per source (0 = all entries from feeds, no cap)",
    )
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    try:
        require_database_url()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    sources = ALL_SOURCES if args.source.lower() == "all" else [args.source.lower()]
    for name in sources:
        get_crawler(name)

    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
    known_ids = KnownIds(load_known_ids())

    limit_label = "unlimited (all feed entries)" if args.limit <= 0 else str(args.limit)

    logger.info("Fetch started (run_id=%s)", run_id)
    logger.info("Database:     %s", get_database_url())
    logger.info("Known articles (all sources, deduped): %d", len(known_ids))
    logger.info("Sources:      %s", ", ".join(sources))
    logger.info("Limit/source: %s", limit_label)

    result = run_all_sources(
        sources,
        run_id=run_id,
        limit=args.limit,
        delay_seconds=args.delay,
        known_ids=known_ids,
    )

    logger.info("Done (all sources).")
    logger.info("  New articles inserted: %d", result.total_saved)
    logger.info("  Duplicates skipped:    %d (already stored)", result.total_skipped)
    logger.info("  Failed (per-article):  %d", result.total_failed)
    if result.sources_crashed:
        logger.error("  Sources that crashed entirely: %s", ", ".join(result.sources_crashed))
    return 0 if (result.total_failed == 0 and not result.sources_crashed) or result.total_saved > 0 else 1


if __name__ == "__main__":
    # Standalone CLI usage (not via the scheduler, which configures its own
    # handlers on the "ingestion" logger) — make output visible in the terminal.
    if not logging.getLogger("ingestion").handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())

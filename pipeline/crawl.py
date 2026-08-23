#!/usr/bin/env python3
"""Crawl articles from Israeli news sources into PostgreSQL."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.hashing import article_id_from_url
from src.crawling.extract_article import build_article_record
from src.crawling.registry import ALL_SOURCES, get_crawler
from src.crawling.rss_utils import NO_LIMIT
from src.db.analysis import maybe_analyze_windows_after_save
from src.db.articles import load_known_ids, save_article
from src.db.classification import ensure_classification_schema, maybe_classify_after_save
from src.db.config import get_database_url, require_database_url
from src.lexicon.load_lexicon import load_article_lexicon

# Child of the "ingestion" logger configured in src/scheduler/ingestion_scheduler.py
# (rotating file + console handlers attached there). When this module is run
# directly as a CLI (not via the scheduler), __main__ below attaches its own
# basicConfig so output still shows up in the terminal as before.
logger = logging.getLogger("ingestion.crawl")


def crawl_source(
    source: str,
    *,
    limit: int,
    delay: float,
    run_id: str,
    known_ids: set[str],
    classify: bool,
    article_lexicon: dict[str, int],
    lexicon_version: str,
) -> tuple[int, int, int]:
    logger.info("Source being scraped: %s", source)
    crawler = get_crawler(source)
    urls = crawler.discover_urls(limit)
    logger.info("%s: %d articles found (RSS/feed discovery)", source, len(urls))

    saved = skipped = failed = 0

    for index, url in enumerate(urls, start=1):
        aid = article_id_from_url(url)
        if aid in known_ids:
            logger.debug("[%d/%d] SKIP (duplicate): %s", index, len(urls), url)
            skipped += 1
            continue

        logger.debug("[%d/%d] Fetching: %s", index, len(urls), url)
        try:
            article = crawler.extract_article(url)
            record = build_article_record(
                source=crawler.source_name,
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
            maybe_classify_after_save(record, enabled=classify)
            maybe_analyze_windows_after_save(record, article_lexicon, lexicon_version)
            saved += 1
            known_ids.add(aid)
        except Exception as exc:
            logger.error("  FAILED to fetch/save %s: %s", url, exc, exc_info=True)
            failed += 1

        time.sleep(delay)

    logger.info(
        "%s: new articles inserted=%d, duplicates skipped=%d, failed=%d",
        source, saved, skipped, failed,
    )
    return saved, skipped, failed


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
    parser.add_argument(
        "--no-classify",
        action="store_true",
        help="Skip AI category labeling after saving each article",
    )
    args = parser.parse_args()

    try:
        require_database_url()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    classify = not args.no_classify
    if classify:
        ensure_classification_schema()

    sources = ALL_SOURCES if args.source.lower() == "all" else [args.source.lower()]
    for name in sources:
        get_crawler(name)

    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
    known_ids = load_known_ids()
    article_lexicon, lexicon_version = load_article_lexicon()

    limit_label = "unlimited (all feed entries)" if args.limit <= 0 else str(args.limit)

    logger.info("Fetch started (run_id=%s)", run_id)
    logger.info("Database:     %s", get_database_url())
    logger.info("Classify:     %s", "on (OpenAI)" if classify else "off")
    logger.info("Known articles (all sources, deduped): %d", len(known_ids))
    logger.info("Sources:      %s", ", ".join(sources))
    logger.info("Limit/source: %s", limit_label)

    total_saved = total_skipped = total_failed = 0
    sources_crashed: list[str] = []
    for source in sources:
        # Fault tolerance: a single source raising (feed timeout, parser bug,
        # site markup change, ...) must never stop the remaining sources —
        # this loop previously had no protection here, so one bad source
        # silently killed the whole scheduled run.
        try:
            saved, skipped, failed = crawl_source(
                source,
                limit=args.limit,
                delay=args.delay,
                run_id=run_id,
                known_ids=known_ids,
                classify=classify,
                article_lexicon=article_lexicon,
                lexicon_version=lexicon_version,
            )
        except Exception as exc:
            logger.error("Source %s crashed and was skipped: %s", source, exc, exc_info=True)
            sources_crashed.append(source)
            continue
        total_saved += saved
        total_skipped += skipped
        total_failed += failed

    logger.info("Done (all sources).")
    logger.info("  New articles inserted: %d", total_saved)
    logger.info("  Duplicates skipped:    %d (already stored)", total_skipped)
    logger.info("  Failed (per-article):  %d", total_failed)
    if sources_crashed:
        logger.error("  Sources that crashed entirely: %s", ", ".join(sources_crashed))
    return 0 if (total_failed == 0 and not sources_crashed) or total_saved > 0 else 1


if __name__ == "__main__":
    # Standalone CLI usage (not via the scheduler, which configures its own
    # handlers on the "ingestion" logger) — make output visible in the terminal.
    if not logging.getLogger("ingestion").handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())

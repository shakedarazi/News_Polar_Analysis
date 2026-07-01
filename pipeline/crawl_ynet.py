#!/usr/bin/env python3
"""Crawl articles from ynet into PostgreSQL."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.hashing import article_id_from_url
from src.crawling.extract_article import build_article_record
from src.crawling.sources.ynet import YnetCrawler
from src.crawling.rss_utils import NO_LIMIT
from src.db.articles import load_known_ids, save_article
from src.db.classification import ensure_classification_schema, maybe_classify_after_save
from src.db.config import get_database_url, require_database_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl ynet articles to PostgreSQL")
    parser.add_argument(
        "--limit",
        type=int,
        default=NO_LIMIT,
        help="Max articles to fetch (0 = all feed entries)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between requests",
    )
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

    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
    known_ids = load_known_ids()

    print(f"Ingestion run: {run_id}")
    print(f"Database:     {get_database_url()}")
    print(f"Classify:     {'on (OpenAI)' if classify else 'off'}")
    print(f"Known articles: {len(known_ids)}")
    print(f"Fetching: {args.limit if args.limit > 0 else 'all feed entries'}...\n")

    crawler = YnetCrawler()
    urls = crawler.discover_urls(args.limit)
    print(f"Discovered {len(urls)} URLs from RSS\n")

    saved = 0
    skipped = 0
    failed = 0

    for index, url in enumerate(urls, start=1):
        aid = article_id_from_url(url)
        if aid in known_ids:
            print(f"[{index}/{len(urls)}] SKIP (already exists): {url}")
            skipped += 1
            continue

        print(f"[{index}/{len(urls)}] Fetching: {url}")
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
            print(f"  OK: {article['title'][:70]}")
            print(f"      {len(article['text'])} chars -> db:{record['article_id'][:16]}…")
            maybe_classify_after_save(record, enabled=classify)
            print()
            saved += 1
            known_ids.add(aid)
        except Exception as exc:
            print(f"  FAILED: {exc}\n")
            failed += 1

        if index < len(urls):
            time.sleep(args.delay)

    print("Done.")
    print(f"  Saved:   {saved}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    return 0 if failed == 0 or saved > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

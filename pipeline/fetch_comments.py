#!/usr/bin/env python3
"""Fetch audience comments for stored articles."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.crawling.comments.fetch_policy import (
    is_permanent_comment_failure,
    select_comment_fetch_batch,
)
from src.crawling.comments.registry import (
    ALL_COMMENT_SOURCES,
    UNSUPPORTED_SOURCES,
    get_comment_fetcher,
    supports_comments,
)
from src.db.comments import (
    iter_articles_for_comment_fetch,
    mark_unsupported_sources_fetched,
    save_comments,
)
from src.db.config import require_database_url
from src.db.migrations import apply_migrations


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch comments for articles in PostgreSQL")
    parser.add_argument(
        "--source",
        default="all",
        help=f"Source or 'all'. Supported: {', '.join(ALL_COMMENT_SOURCES)}",
    )
    parser.add_argument(
        "--min-age-hours",
        type=int,
        default=24,
        help="Only articles at least this old (default: 24h per RFC)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max articles (0 = all)")
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument(
        "--max-minutes",
        type=float,
        default=0,
        help="Stop starting new fetches after this many minutes (0 = no cap)",
    )
    parser.add_argument(
        "--haaretz-limit",
        type=int,
        default=0,
        help="Max Haaretz articles this run (0 = no extra cap). Playwright is slow.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if comments_fetched_at is set",
    )
    args = parser.parse_args()

    try:
        require_database_url()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    apply_migrations()

    if args.source.lower() == "all":
        sources = ALL_COMMENT_SOURCES
    else:
        source = args.source.lower()
        if source not in ALL_COMMENT_SOURCES:
            supported = ", ".join(ALL_COMMENT_SOURCES)
            print(f"ERROR: '{source}' has no comment fetcher. Supported: {supported}", file=sys.stderr)
            if source in UNSUPPORTED_SOURCES:
                print(f"Note: {source} requires browser rendering or has no public comments.", file=sys.stderr)
            return 1
        sources = [source]

    pending = iter_articles_for_comment_fetch(
        sources=sources,
        min_age_hours=args.min_age_hours,
        missing_only=not args.force,
        limit=None,
    )
    per_source_caps = {"haaretz": args.haaretz_limit} if args.haaretz_limit > 0 else None
    overall_limit = None if args.limit <= 0 else args.limit
    articles = select_comment_fetch_batch(
        pending,
        limit=overall_limit,
        per_source_caps=per_source_caps,
    )
    deferred = len(pending) - len(articles)

    run_id = datetime.now(timezone.utc).strftime("comments_%Y%m%d_%H%M%S")
    print(f"Comment fetch run: {run_id}")
    print(f"Sources:           {', '.join(sources)}")
    print(f"Min article age:   {args.min_age_hours}h")
    print(f"Pending:           {len(pending)}")
    print(f"This run:          {len(articles)}")
    if deferred:
        print(f"Deferred:          {deferred} (limit/source cap; next run)")
    if args.max_minutes > 0:
        print(f"Time budget:       {args.max_minutes:g} min")
    if UNSUPPORTED_SOURCES:
        print(f"Not supported:     {', '.join(sorted(UNSUPPORTED_SOURCES))}")
    print()

    if not articles:
        marked = mark_unsupported_sources_fetched(min_age_hours=args.min_age_hours)
        if marked:
            print(f"Marked {marked} unsupported-source article(s) as fetched (no comment API).")
        print("Nothing to fetch.")
        return 0

    fetched = skipped = failed = gave_up = 0
    total_inserted = 0
    started = time.monotonic()
    stopped_for_time = False

    for index, article in enumerate(articles, start=1):
        if args.max_minutes > 0 and (time.monotonic() - started) >= args.max_minutes * 60:
            leftover = len(articles) - index + 1
            print(
                f"Reached --max-minutes={args.max_minutes:g}; "
                f"{leftover} article(s) left for a later run."
            )
            skipped += leftover
            stopped_for_time = True
            break

        source = article["source"]
        url = article["canonical_url"]
        title = (article.get("title") or "")[:60]
        print(f"[{index}/{len(articles)}] {source}: {title}")

        if not supports_comments(source):
            print("  SKIP: no comment fetcher for this source\n")
            skipped += 1
            continue

        fetcher = get_comment_fetcher(source)
        try:
            comments = fetcher(url)
            inserted = save_comments(
                article["article_id"],
                source,
                comments,
                fetch_run_id=run_id,
            )
            print(f"  OK: {len(comments)} comments ({inserted} new)\n")
            fetched += 1
            total_inserted += inserted
        except Exception as exc:
            if is_permanent_comment_failure(exc):
                save_comments(
                    article["article_id"],
                    source,
                    [],
                    fetch_run_id=run_id,
                )
                print(f"  GAVE UP (permanent, marked fetched with 0 comments): {exc}\n")
                gave_up += 1
            else:
                print(f"  FAILED (transient, will retry): {exc}\n")
                failed += 1

        if index < len(articles) and not stopped_for_time:
            time.sleep(args.delay)

    print("Done.")
    print(f"  Articles processed: {fetched}")
    print(f"  Comments inserted:  {total_inserted}")
    print(f"  Gave up (permanent): {gave_up}")
    print(f"  Skipped:            {skipped}")
    print(f"  Failed (transient): {failed}")

    marked = mark_unsupported_sources_fetched(min_age_hours=args.min_age_hours)
    if marked:
        print(f"  Unsupported marked: {marked} (reshet13 — no public comment system)")

    # Same rule as crawl: partial per-article failure is not a step failure
    # when anything progressed (fetched or permanently closed out).
    return 0 if failed == 0 or (fetched + gave_up) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

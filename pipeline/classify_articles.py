#!/usr/bin/env python3
"""Classify articles into news categories using OpenAI."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.classification import (
    ensure_classification_schema,
    iter_articles_for_classification,
    save_classification,
)
from src.db.config import require_database_url
from src.nlp.categories import CATEGORIES, DEFAULT_MODEL
from src.nlp.classify import classify_article
from src.nlp.openai_config import require_openai_api_key


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Label articles with AI categories (OpenAI)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        help="Re-classify all articles (not only missing)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max articles (0 = all)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")
    parser.add_argument(
        "--max-minutes",
        type=float,
        default=0,
        help="Stop starting new API calls after this many minutes (0 = no cap)",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model name")
    parser.add_argument("--dry-run", action="store_true", help="List articles, do not call API")
    args = parser.parse_args()

    missing_only = not args.all

    try:
        require_database_url()
        require_openai_api_key()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    ensure_classification_schema()

    limit = None if args.limit <= 0 else args.limit
    articles = iter_articles_for_classification(missing_only=missing_only, limit=limit)

    mode = "missing only" if missing_only else "all articles"
    print(f"Categories: {', '.join(CATEGORIES)}")
    print(f"Model:      {args.model}")
    print(f"Mode:       {mode}")
    print(f"Articles:   {len(articles)}")
    if args.max_minutes > 0:
        print(f"Time budget: {args.max_minutes:g} min")
    print()

    if not articles:
        print("Nothing to classify.")
        return 0

    if args.dry_run:
        for article in articles:
            print(f"  {article['article_id'][:16]}… [{article['source']}] {article['title'][:60]}")
        return 0

    classified = failed = 0
    started = time.monotonic()
    for index, article in enumerate(articles, start=1):
        if args.max_minutes > 0 and (time.monotonic() - started) >= args.max_minutes * 60:
            leftover = len(articles) - index + 1
            print(
                f"Reached --max-minutes={args.max_minutes:g}; "
                f"{leftover} article(s) left for a later run."
            )
            break
        title_preview = (article["title"] or "")[:60]
        print(f"[{index}/{len(articles)}] {article['source']}: {title_preview}")
        try:
            result = classify_article(
                title=article["title"],
                text=article["text"],
                source=article["source"],
                model=args.model,
            )
            save_classification(article["article_id"], result)
            print(
                f"  -> {result.primary_category} "
                f"({result.confidence:.0%}) — {result.rationale}\n"
            )
            classified += 1
        except Exception as exc:
            print(f"  FAILED: {exc}\n")
            failed += 1

        if index < len(articles):
            time.sleep(args.delay)

    print(f"Done. classified={classified} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

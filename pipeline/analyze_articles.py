#!/usr/bin/env python3
"""Run lexicon-based polarity analysis on stored articles and comments."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.aggregation import aggregate_comments
from src.analysis.article_windows import extract_window_features
from src.analysis.comments_scoring import score_comment
from src.db.analysis import (
    fetch_comments_for_article,
    iter_articles_for_analysis,
    save_analysis,
)
from src.db.config import require_database_url
from src.db.migrations import apply_migrations
from src.lexicon.load_lexicon import load_article_lexicon, load_comment_lexicon


def main() -> int:
    parser = argparse.ArgumentParser(description="Lexicon-based polarity analysis")
    parser.add_argument("--min-age-hours", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Re-analyze already processed articles")
    parser.add_argument(
        "--include-stale",
        action="store_true",
        help="Re-analyze when comments were fetched after last analysis",
    )
    parser.add_argument(
        "--require-comments-fetched",
        action="store_true",
        help="Only articles that completed comment fetch (or unsupported mark)",
    )
    args = parser.parse_args()

    try:
        require_database_url()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    apply_migrations()

    article_lexicon, lexicon_version = load_article_lexicon()
    comment_lexicon, comment_lexicon_version = load_comment_lexicon()

    limit = None if args.limit <= 0 else args.limit
    articles = iter_articles_for_analysis(
        min_age_hours=args.min_age_hours,
        missing_only=not args.force,
        include_stale=args.include_stale,
        require_comments_fetched=args.require_comments_fetched,
        limit=limit,
    )

    run_id = datetime.now(timezone.utc).strftime("analysis_%Y%m%d_%H%M%S")
    print(f"Analysis run: {run_id}")
    print(f"Articles:     {len(articles)}")
    print(f"Lexicon:      {lexicon_version[:16]}...")
    print(f"Comment lex:  {comment_lexicon_version[:16]}...")
    print()

    if not articles:
        print("Nothing to analyze.")
        return 0

    processed = failed = 0
    total_windows = 0
    total_comments = 0

    for index, article in enumerate(articles, start=1):
        article_id = article["article_id"]
        title = (article.get("title") or "")[:60]
        print(f"[{index}/{len(articles)}] {article['source']}: {title}")

        try:
            windows = extract_window_features(article["text"], article_lexicon)
            raw_comments = fetch_comments_for_article(article_id)
            comment_features = [
                score_comment(
                    comment_id=row["comment_id"],
                    text=row["text"],
                    polar_lexicon=comment_lexicon,
                    like_count=int(row.get("like_count") or 0),
                    dislike_count=0,
                )
                for row in raw_comments
            ]
            agg = aggregate_comments(article_id, comment_features)
            save_analysis(
                article_id,
                windows=windows,
                comment_features=comment_features,
                aggregate=agg,
                lexicon_version=lexicon_version,
                comment_lexicon_version=comment_lexicon_version,
                run_id=run_id,
            )
            print(
                f"  OK: {len(windows)} windows, {len(comment_features)} comments, "
                f"audience_mean={agg.audience_mean}"
            )
            processed += 1
            total_windows += len(windows)
            total_comments += len(comment_features)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failed += 1
        print()

    print("Done.")
    print(f"  Processed: {processed}")
    print(f"  Windows:   {total_windows}")
    print(f"  Comments:  {total_comments}")
    print(f"  Failed:    {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

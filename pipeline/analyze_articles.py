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
from src.analysis.comments_scoring import engagement_weight, score_comment
from src.analysis.polarization_scoring import (
    aggregate_polarization,
    load_polarization_lexicon_for_scoring,
    score_comment_polarization,
)
from src.db.analysis import (
    fetch_comments_for_article,
    iter_articles_for_analysis,
    iter_articles_missing_polarization,
    iter_articles_missing_windows,
    save_analysis,
    save_polarization,
    save_window_features,
)
from src.db.config import require_database_url
from src.db.migrations import apply_migrations
from src.lexicon.load_lexicon import load_article_lexicon, load_comment_lexicon


def _run_windows_only(article_lexicon: dict, lexicon_version: str, limit: int | None) -> int:
    articles = iter_articles_missing_windows(limit=limit)
    run_id = datetime.now(timezone.utc).strftime("windows_%Y%m%d_%H%M%S")
    print(f"Windows-only backfill run: {run_id}")
    print(f"Articles:     {len(articles)}")
    print(f"Lexicon:      {lexicon_version[:16]}...")
    print()

    if not articles:
        print("Nothing to backfill.")
        return 0

    processed = failed = 0
    for index, article in enumerate(articles, start=1):
        title = (article.get("title") or "")[:60]
        print(f"[{index}/{len(articles)}] {article['source']}: {title}")
        try:
            windows = extract_window_features(article["text"], article_lexicon)
            save_window_features(
                article["article_id"], windows, lexicon_version=lexicon_version, run_id=run_id
            )
            print(f"  OK: {len(windows)} windows")
            processed += 1
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failed += 1

    print()
    print("Done.")
    print(f"  Processed: {processed}")
    print(f"  Failed:    {failed}")
    return 0 if failed == 0 or processed > 0 else 1


def _run_polarization_only(
    polarization_lexicon: dict,
    polarization_lexicon_version: str,
    limit: int | None,
) -> int:
    """Score already-analyzed comments on the research lexicon only.

    Exists for the same reason --windows-only does: the ~50k comments stored
    before these columns existed need a pass over them, and re-running the whole
    analysis to get it would redo window extraction and the single-axis score
    for every one of them. This touches five columns and reads nothing else.
    """
    articles = iter_articles_missing_polarization(polarization_lexicon_version, limit=limit)
    print("Polarization-only backfill")
    print(f"Articles:     {len(articles)}")
    print(f"Polar lex:    {polarization_lexicon_version[:16]}...")
    print()

    if not articles:
        print("Nothing to backfill.")
        return 0

    processed = failed = 0
    for index, article in enumerate(articles, start=1):
        article_id = article["article_id"]
        title = (article.get("title") or "")[:60]
        print(f"[{index}/{len(articles)}] {article['source']}: {title}")
        try:
            raw_comments = fetch_comments_for_article(article_id)
            polarization = [
                score_comment_polarization(
                    comment_id=row["comment_id"],
                    text=row["text"],
                    polarization_lexicon=polarization_lexicon,
                )
                for row in raw_comments
            ]
            # Recomputed rather than read back: engagement_weight is a pure
            # function of like_count, and both aggregates must weight a comment
            # the same way or the two readings diverge for two reasons at once.
            weighted = [
                (feature, engagement_weight(int(row.get("like_count") or 0)))
                for feature, row in zip(polarization, raw_comments, strict=True)
            ]
            save_polarization(
                article_id,
                polarization=polarization,
                aggregate=aggregate_polarization(article_id, weighted),
                polarization_lexicon_version=polarization_lexicon_version,
            )
            print(f"  OK: {len(polarization)} comments")
            processed += 1
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failed += 1

    print()
    print("Done.")
    print(f"  Processed: {processed}")
    print(f"  Failed:    {failed}")
    return 0 if failed == 0 or processed > 0 else 1


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
    parser.add_argument(
        "--windows-only",
        action="store_true",
        help=(
            "Backfill article-text (dominance) analysis only, for articles with none yet — "
            "no age/comments-fetched gate, since this doesn't depend on comments. "
            "New crawls get this automatically (see maybe_analyze_windows_after_save); "
            "use this to catch up articles crawled before that existed."
        ),
    )
    parser.add_argument(
        "--polarization-only",
        action="store_true",
        help=(
            "Backfill the two-axis (research lexicon) comment scores only, for "
            "articles already analyzed whose comments lack them or were scored "
            "on a different lexicon version. Skips windows and the single-axis "
            "score entirely."
        ),
    )
    args = parser.parse_args()

    try:
        require_database_url()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    apply_migrations()

    limit = None if args.limit <= 0 else args.limit
    polarization_lexicon, polarization_lexicon_version = load_polarization_lexicon_for_scoring()

    if args.polarization_only:
        return _run_polarization_only(
            polarization_lexicon, polarization_lexicon_version, limit
        )

    article_lexicon, lexicon_version = load_article_lexicon()

    if args.windows_only:
        return _run_windows_only(article_lexicon, lexicon_version, limit)

    comment_lexicon, comment_lexicon_version = load_comment_lexicon()
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
    print(f"Polar lex:    {polarization_lexicon_version[:16]}...")
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
            # The second reading of the same comments (docs/adr/0004). Same
            # text, same denominator, same like weights — different lexicon.
            polarization = [
                score_comment_polarization(
                    comment_id=row["comment_id"],
                    text=row["text"],
                    polarization_lexicon=polarization_lexicon,
                )
                for row in raw_comments
            ]
            polarization_agg = aggregate_polarization(
                article_id,
                [
                    (polar, feature.engagement_weight)
                    for polar, feature in zip(polarization, comment_features, strict=True)
                ],
            )
            save_analysis(
                article_id,
                windows=windows,
                comment_features=comment_features,
                aggregate=agg,
                polarization=polarization,
                polarization_aggregate=polarization_agg,
                lexicon_version=lexicon_version,
                comment_lexicon_version=comment_lexicon_version,
                polarization_lexicon_version=polarization_lexicon_version,
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
    return 0 if failed == 0 or processed > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

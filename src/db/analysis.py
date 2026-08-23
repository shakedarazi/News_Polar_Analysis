"""Persist lexicon-based analysis results."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.analysis.aggregation import ArticleCommentAgg
from src.analysis.article_windows import WindowFeatures
from src.analysis.comments_scoring import CommentFeatures
from src.db.config import require_database_url
from src.db.connection import get_connection

PIPELINE_VERSION = "1.0.0"


def iter_articles_for_analysis(
    *,
    min_age_hours: int = 0,
    missing_only: bool = True,
    include_stale: bool = False,
    require_comments_fetched: bool = False,
    limit: int | None = None,
) -> list[dict]:
    require_database_url()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)
    query = """
        SELECT a.article_id, a.source, a.title, a.text, a.canonical_url, a.first_seen_at
        FROM articles a
        WHERE a.first_seen_at <= %s
    """
    params: list = [cutoff]
    if require_comments_fetched:
        query += " AND a.comments_fetched_at IS NOT NULL"
    if missing_only and not include_stale:
        query += " AND a.analyzed_at IS NULL"
    elif missing_only and include_stale:
        query += """
            AND (
                a.analyzed_at IS NULL
                OR (a.comments_fetched_at IS NOT NULL AND a.comments_fetched_at > a.analyzed_at)
            )
        """
    query += " ORDER BY a.first_seen_at DESC"
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetch_comments_for_article(article_id: str) -> list[dict]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT comment_id, text, like_count
                FROM comments
                WHERE article_id = %s
                ORDER BY comment_id
                """,
                (article_id,),
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def save_window_features(
    article_id: str,
    windows: list[WindowFeatures],
    *,
    lexicon_version: str,
    run_id: str,
) -> None:
    """Persist article-text (dominance) analysis only — independent of
    comments, so it can run immediately after crawl instead of waiting on
    the 24h/comments-fetched gate that comment-based audience analysis needs."""
    require_database_url()
    now = datetime.now(timezone.utc)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for window in windows:
                cur.execute(
                    """
                    INSERT INTO windows_features (
                        article_id, sentence_idx, window_len,
                        c1, c2, c3, c4, c5, c6, c7,
                        active, dominance,
                        lexicon_version, pipeline_version, run_id, analyzed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (article_id, sentence_idx, lexicon_version, pipeline_version)
                    DO UPDATE SET
                        window_len = EXCLUDED.window_len,
                        c1 = EXCLUDED.c1, c2 = EXCLUDED.c2, c3 = EXCLUDED.c3,
                        c4 = EXCLUDED.c4, c5 = EXCLUDED.c5, c6 = EXCLUDED.c6, c7 = EXCLUDED.c7,
                        active = EXCLUDED.active,
                        dominance = EXCLUDED.dominance,
                        run_id = EXCLUDED.run_id,
                        analyzed_at = EXCLUDED.analyzed_at
                    """,
                    (
                        article_id,
                        window.sentence_idx,
                        window.window_len,
                        window.c1,
                        window.c2,
                        window.c3,
                        window.c4,
                        window.c5,
                        window.c6,
                        window.c7,
                        window.active,
                        window.dominance,
                        lexicon_version,
                        PIPELINE_VERSION,
                        run_id,
                        now,
                    ),
                )


def iter_articles_missing_windows(limit: int | None = None) -> list[dict]:
    """Articles with no article-text (dominance) analysis yet — no age or
    comments-fetched gate, since this analysis doesn't depend on comments."""
    require_database_url()
    query = """
        SELECT a.article_id, a.source, a.title, a.text
        FROM articles a
        WHERE NOT EXISTS (
            SELECT 1 FROM windows_features w WHERE w.article_id = a.article_id
        )
        ORDER BY a.first_seen_at DESC
    """
    params: list = []
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def maybe_analyze_windows_after_save(
    record: dict,
    article_lexicon: dict[str, int],
    lexicon_version: str,
    *,
    enabled: bool = True,
) -> None:
    """Compute + persist article-text analysis right after a crawl save.
    Comment-based audience analysis still waits for the 24h/comments-fetched
    gate (see analyze_articles.py) — this only covers the article text
    itself, which needs nothing but what's already in `record`."""
    if not enabled:
        return
    from src.analysis.article_windows import extract_window_features

    try:
        windows = extract_window_features(record["text"], article_lexicon)
        run_id = datetime.now(timezone.utc).strftime("windows_%Y%m%d_%H%M%S")
        save_window_features(
            record["article_id"], windows, lexicon_version=lexicon_version, run_id=run_id
        )
    except Exception as exc:
        print(f"  WARN: article-text analysis failed ({exc}) — article saved without it")


def save_analysis(
    article_id: str,
    *,
    windows: list[WindowFeatures],
    comment_features: list[CommentFeatures],
    aggregate: ArticleCommentAgg,
    lexicon_version: str,
    comment_lexicon_version: str,
    run_id: str,
) -> None:
    require_database_url()
    now = datetime.now(timezone.utc)

    save_window_features(article_id, windows, lexicon_version=lexicon_version, run_id=run_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for feature in comment_features:
                cur.execute(
                    """
                    INSERT INTO comments_features (
                        comment_id, article_id, comment_len, polar_count, polar_ratio,
                        like_count, dislike_count, engagement_weight, comment_score,
                        controversy, comment_lexicon_version, pipeline_version, run_id, analyzed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (comment_id, comment_lexicon_version, pipeline_version)
                    DO UPDATE SET
                        comment_len = EXCLUDED.comment_len,
                        polar_count = EXCLUDED.polar_count,
                        polar_ratio = EXCLUDED.polar_ratio,
                        like_count = EXCLUDED.like_count,
                        dislike_count = EXCLUDED.dislike_count,
                        engagement_weight = EXCLUDED.engagement_weight,
                        comment_score = EXCLUDED.comment_score,
                        controversy = EXCLUDED.controversy,
                        run_id = EXCLUDED.run_id,
                        analyzed_at = EXCLUDED.analyzed_at
                    """,
                    (
                        feature.comment_id,
                        article_id,
                        feature.comment_len,
                        feature.polar_count,
                        feature.polar_ratio,
                        feature.like_count,
                        feature.dislike_count,
                        feature.engagement_weight,
                        feature.comment_score,
                        feature.controversy,
                        comment_lexicon_version,
                        PIPELINE_VERSION,
                        run_id,
                        now,
                    ),
                )

            cur.execute(
                """
                INSERT INTO article_comments_agg (
                    article_id, num_comments, audience_mean, audience_p85,
                    controversy_mean, controversy_p85, sum_engagement_weight,
                    comment_lexicon_version, pipeline_version, run_id, analyzed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (article_id, comment_lexicon_version, pipeline_version)
                DO UPDATE SET
                    num_comments = EXCLUDED.num_comments,
                    audience_mean = EXCLUDED.audience_mean,
                    audience_p85 = EXCLUDED.audience_p85,
                    controversy_mean = EXCLUDED.controversy_mean,
                    controversy_p85 = EXCLUDED.controversy_p85,
                    sum_engagement_weight = EXCLUDED.sum_engagement_weight,
                    run_id = EXCLUDED.run_id,
                    analyzed_at = EXCLUDED.analyzed_at
                """,
                (
                    article_id,
                    aggregate.num_comments,
                    aggregate.audience_mean,
                    aggregate.audience_p85,
                    aggregate.controversy_mean,
                    aggregate.controversy_p85,
                    aggregate.sum_engagement_weight,
                    comment_lexicon_version,
                    PIPELINE_VERSION,
                    run_id,
                    now,
                ),
            )

            cur.execute(
                "UPDATE articles SET analyzed_at = %s WHERE article_id = %s",
                (now, article_id),
            )

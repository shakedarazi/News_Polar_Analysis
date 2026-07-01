"""Read-only queries for the browse API."""

from __future__ import annotations

from src.db.config import require_database_url
from src.db.connection import get_connection


def list_articles(
    *,
    source: str | None = None,
    category: str | None = None,
    min_audience_mean: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    require_database_url()
    query = """
        SELECT
            a.article_id,
            a.source,
            a.title,
            a.canonical_url,
            a.primary_category,
            a.category_confidence,
            a.first_seen_at,
            a.analyzed_at,
            agg.num_comments,
            agg.audience_mean,
            agg.audience_p85,
            agg.controversy_mean
        FROM articles a
        LEFT JOIN LATERAL (
            SELECT num_comments, audience_mean, audience_p85, controversy_mean
            FROM article_comments_agg
            WHERE article_id = a.article_id
            ORDER BY analyzed_at DESC
            LIMIT 1
        ) agg ON TRUE
        WHERE 1=1
    """
    params: list = []
    if source:
        query += " AND a.source = %s"
        params.append(source.lower())
    if category:
        query += " AND a.primary_category = %s"
        params.append(category)
    if min_audience_mean is not None:
        query += " AND agg.audience_mean >= %s"
        params.append(min_audience_mean)
    query += " ORDER BY a.first_seen_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def get_article_detail(article_id: str) -> dict | None:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT article_id, source, title, text, canonical_url,
                       primary_category, category_confidence, category_rationale,
                       first_seen_at, analyzed_at, comments_fetched_at
                FROM articles
                WHERE article_id = %s
                """,
                (article_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cur.description]
            article = dict(zip(columns, row))

            cur.execute(
                """
                SELECT num_comments, audience_mean, audience_p85,
                       controversy_mean, controversy_p85, sum_engagement_weight, analyzed_at
                FROM article_comments_agg
                WHERE article_id = %s
                ORDER BY analyzed_at DESC
                LIMIT 1
                """,
                (article_id,),
            )
            agg_row = cur.fetchone()
            article["aggregation"] = None
            if agg_row:
                agg_cols = [d[0] for d in cur.description]
                article["aggregation"] = dict(zip(agg_cols, agg_row))

            cur.execute(
                """
                SELECT sentence_idx, window_len, c1, c2, c3, c4, c5, c6, c7, active, dominance
                FROM windows_features
                WHERE article_id = %s
                ORDER BY sentence_idx
                LIMIT 100
                """,
                (article_id,),
            )
            win_cols = [d[0] for d in cur.description]
            article["windows"] = [dict(zip(win_cols, r)) for r in cur.fetchall()]

            cur.execute(
                """
                SELECT c.comment_id, c.text, c.author, c.like_count,
                       cf.polar_ratio, cf.comment_score, cf.controversy
                FROM comments c
                LEFT JOIN LATERAL (
                    SELECT polar_ratio, comment_score, controversy
                    FROM comments_features
                    WHERE comment_id = c.comment_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) cf ON TRUE
                WHERE c.article_id = %s
                ORDER BY cf.polar_ratio DESC NULLS LAST, c.like_count DESC
                LIMIT 50
                """,
                (article_id,),
            )
            com_cols = [d[0] for d in cur.description]
            article["comments"] = [dict(zip(com_cols, r)) for r in cur.fetchall()]

            return article


def list_sources() -> list[dict]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source, COUNT(*) AS article_count
                FROM articles
                GROUP BY source
                ORDER BY article_count DESC
                """
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def list_categories() -> list[dict]:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT primary_category AS category, COUNT(*) AS article_count
                FROM articles
                WHERE primary_category IS NOT NULL
                GROUP BY primary_category
                ORDER BY article_count DESC
                """
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def get_dashboard_stats() -> dict:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM articles")
            total_articles = int(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM comments")
            total_comments = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT AVG(agg.audience_mean)
                FROM article_comments_agg agg
                WHERE agg.audience_mean IS NOT NULL
                """
            )
            avg_polar = cur.fetchone()[0]

            cur.execute(
                """
                SELECT a.source, COUNT(*) AS cnt
                FROM articles a
                GROUP BY a.source
                ORDER BY cnt DESC
                LIMIT 1
                """
            )
            top_source_row = cur.fetchone()
            top_source = top_source_row[0] if top_source_row else None

            cur.execute(
                """
                SELECT a.source,
                       COUNT(*) AS article_count,
                       AVG(agg.audience_mean) AS avg_audience_mean
                FROM articles a
                LEFT JOIN LATERAL (
                    SELECT audience_mean
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                GROUP BY a.source
                ORDER BY article_count DESC
                """
            )
            source_cols = [d[0] for d in cur.description]
            by_source = [dict(zip(source_cols, r)) for r in cur.fetchall()]

            cur.execute(
                """
                SELECT a.primary_category AS category,
                       COUNT(*) AS article_count,
                       AVG(agg.audience_mean) AS avg_audience_mean
                FROM articles a
                LEFT JOIN LATERAL (
                    SELECT audience_mean
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                WHERE a.primary_category IS NOT NULL
                GROUP BY a.primary_category
                ORDER BY article_count DESC
                """
            )
            cat_cols = [d[0] for d in cur.description]
            by_category = [dict(zip(cat_cols, r)) for r in cur.fetchall()]

            cur.execute(
                """
                SELECT a.article_id, a.source, a.title, a.primary_category,
                       agg.audience_mean, agg.audience_p85, agg.num_comments
                FROM articles a
                JOIN LATERAL (
                    SELECT audience_mean, audience_p85, num_comments
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                WHERE agg.audience_p85 IS NOT NULL
                ORDER BY agg.audience_p85 DESC
                LIMIT 10
                """
            )
            hot_cols = [d[0] for d in cur.description]
            hottest = [dict(zip(hot_cols, r)) for r in cur.fetchall()]

            return {
                "total_articles": total_articles,
                "total_comments": total_comments,
                "avg_audience_mean": float(avg_polar) if avg_polar is not None else None,
                "top_source": top_source,
                "by_source": by_source,
                "by_category": by_category,
                "hottest_articles": hottest,
            }


def count_articles(
    *,
    source: str | None = None,
    category: str | None = None,
    min_audience_mean: float | None = None,
) -> int:
    require_database_url()
    query = """
        SELECT COUNT(*)
        FROM articles a
        LEFT JOIN LATERAL (
            SELECT audience_mean
            FROM article_comments_agg
            WHERE article_id = a.article_id
            ORDER BY analyzed_at DESC
            LIMIT 1
        ) agg ON TRUE
        WHERE 1=1
    """
    params: list = []
    if source:
        query += " AND a.source = %s"
        params.append(source.lower())
    if category:
        query += " AND a.primary_category = %s"
        params.append(category)
    if min_audience_mean is not None:
        query += " AND agg.audience_mean >= %s"
        params.append(min_audience_mean)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return int(cur.fetchone()[0])

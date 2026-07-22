"""Read-only queries for the browse API."""

from __future__ import annotations

from src.db.config import require_database_url
from src.db.connection import get_connection

# Polarity level thresholds — must stay in sync with frontend/src/lib/format.ts polarLevel().
POLARITY_HIGH = 0.15
POLARITY_MID = 0.05


def _count_active_events() -> int:
    """Events (src.analysis.event_grouping) still receiving new coverage —
    same "still developing" window as the new_event smart alert."""
    from datetime import datetime, timezone

    from src.analysis.alerts import STILL_DEVELOPING_HOURS
    from src.analysis.event_grouping import get_events

    now = datetime.now(timezone.utc)
    events = get_events(limit=100)
    return sum(
        1
        for e in events
        if (now - e["last_seen_at"]).total_seconds() / 3600.0 <= STILL_DEVELOPING_HOURS
    )


def _common_filters(
    *,
    alias: str = "a",
    source: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[str, list]:
    clauses = ""
    params: list = []
    if source:
        clauses += f" AND {alias}.source = %s"
        params.append(source.lower())
    if category:
        clauses += f" AND {alias}.primary_category = %s"
        params.append(category)
    if start_date:
        clauses += f" AND {alias}.first_seen_at::date >= %s::date"
        params.append(start_date)
    if end_date:
        clauses += f" AND {alias}.first_seen_at::date <= %s::date"
        params.append(end_date)
    return clauses, params


def list_articles(
    *,
    source: str | None = None,
    category: str | None = None,
    min_audience_mean: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    q: str | None = None,
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
            a.bias_label,
            a.bias_score,
            a.bias_confidence,
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
    filter_sql, params = _common_filters(
        source=source, category=category, start_date=start_date, end_date=end_date
    )
    query += filter_sql
    if min_audience_mean is not None:
        query += " AND agg.audience_mean >= %s"
        params.append(min_audience_mean)
    if q:
        query += " AND (a.title ILIKE %s OR a.text ILIKE %s)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern])
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


def get_date_range() -> dict:
    """Global (unfiltered) earliest/latest article dates — used to bound filter UI."""
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MIN(first_seen_at), MAX(first_seen_at) FROM articles")
            min_date, max_date = cur.fetchone()
            return {"min": min_date, "max": max_date}


def get_dashboard_stats(
    *,
    source: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    require_database_url()
    filter_sql, filter_params = _common_filters(
        source=source, category=category, start_date=start_date, end_date=end_date
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) FROM articles a WHERE 1=1 {filter_sql}",
                filter_params,
            )
            total_articles = int(cur.fetchone()[0])

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM comments c
                JOIN articles a ON a.article_id = c.article_id
                WHERE 1=1 {filter_sql}
                """,
                filter_params,
            )
            total_comments = int(cur.fetchone()[0])

            cur.execute(
                f"""
                SELECT AVG(agg.audience_mean)
                FROM articles a
                JOIN LATERAL (
                    SELECT audience_mean
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                WHERE agg.audience_mean IS NOT NULL {filter_sql}
                """,
                filter_params,
            )
            avg_polar = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT a.source, COUNT(*) AS cnt
                FROM articles a
                WHERE 1=1 {filter_sql}
                GROUP BY a.source
                ORDER BY cnt DESC
                LIMIT 1
                """,
                filter_params,
            )
            top_source_row = cur.fetchone()
            top_source = top_source_row[0] if top_source_row else None

            cur.execute(
                f"""
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
                WHERE 1=1 {filter_sql}
                GROUP BY a.source
                ORDER BY article_count DESC
                """,
                filter_params,
            )
            source_cols = [d[0] for d in cur.description]
            by_source = [dict(zip(source_cols, r)) for r in cur.fetchall()]

            cur.execute(
                f"""
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
                WHERE a.primary_category IS NOT NULL {filter_sql}
                GROUP BY a.primary_category
                ORDER BY article_count DESC
                """,
                filter_params,
            )
            cat_cols = [d[0] for d in cur.description]
            by_category = [dict(zip(cat_cols, r)) for r in cur.fetchall()]

            cur.execute(
                f"""
                SELECT a.article_id, a.source, a.title, a.primary_category,
                       a.first_seen_at, a.canonical_url,
                       a.bias_label, a.bias_score, a.bias_confidence,
                       LEFT(a.text, 180) AS snippet,
                       agg.audience_mean, agg.audience_p85, agg.num_comments
                FROM articles a
                JOIN LATERAL (
                    SELECT audience_mean, audience_p85, num_comments
                    FROM article_comments_agg
                    WHERE article_id = a.article_id
                    ORDER BY analyzed_at DESC
                    LIMIT 1
                ) agg ON TRUE
                WHERE agg.audience_p85 IS NOT NULL {filter_sql}
                ORDER BY agg.audience_p85 DESC
                LIMIT 10
                """,
                filter_params,
            )
            hot_cols = [d[0] for d in cur.description]
            hottest = [dict(zip(hot_cols, r)) for r in cur.fetchall()]

            date_range = get_date_range()

            return {
                "total_articles": total_articles,
                "total_comments": total_comments,
                "avg_audience_mean": float(avg_polar) if avg_polar is not None else None,
                "top_source": top_source,
                "by_source": by_source,
                "by_category": by_category,
                "active_events_count": _count_active_events(),
                "hottest_articles": hottest,
                "date_range": date_range,
            }


def get_polarity_trend(
    *,
    source: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Average audience polarity per day, based on article first_seen_at."""
    require_database_url()
    filter_sql, params = _common_filters(
        source=source, category=category, start_date=start_date, end_date=end_date
    )
    query = f"""
        SELECT
            a.first_seen_at::date AS date,
            AVG(agg.audience_mean) AS avg_polarity,
            COUNT(*) FILTER (WHERE agg.audience_mean IS NOT NULL) AS article_count
        FROM articles a
        LEFT JOIN LATERAL (
            SELECT audience_mean
            FROM article_comments_agg
            WHERE article_id = a.article_id
            ORDER BY analyzed_at DESC
            LIMIT 1
        ) agg ON TRUE
        WHERE 1=1 {filter_sql}
        GROUP BY 1
        ORDER BY 1
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            for row in rows:
                if row["avg_polarity"] is not None:
                    row["avg_polarity"] = float(row["avg_polarity"])
            return rows


def get_polarity_by_source(
    *,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Per-source breakdown of article polarity into low/mid/high buckets.

    Buckets reuse the same thresholds as frontend/src/lib/format.ts polarLevel():
    low < 0.05 <= mid < 0.15 <= high.
    """
    require_database_url()
    filter_sql, params = _common_filters(
        source=None, category=category, start_date=start_date, end_date=end_date
    )
    query = f"""
        SELECT
            a.source,
            COUNT(*) FILTER (WHERE agg.audience_mean IS NOT NULL) AS analyzed_count,
            COUNT(*) FILTER (WHERE agg.audience_mean >= {POLARITY_HIGH}) AS high_count,
            COUNT(*) FILTER (
                WHERE agg.audience_mean >= {POLARITY_MID} AND agg.audience_mean < {POLARITY_HIGH}
            ) AS mid_count,
            COUNT(*) FILTER (WHERE agg.audience_mean < {POLARITY_MID}) AS low_count,
            AVG(agg.audience_mean) AS avg_polarity
        FROM articles a
        LEFT JOIN LATERAL (
            SELECT audience_mean
            FROM article_comments_agg
            WHERE article_id = a.article_id
            ORDER BY analyzed_at DESC
            LIMIT 1
        ) agg ON TRUE
        WHERE 1=1 {filter_sql}
        GROUP BY a.source
        ORDER BY analyzed_count DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            for row in rows:
                if row["avg_polarity"] is not None:
                    row["avg_polarity"] = float(row["avg_polarity"])
            return rows


def search_articles_for_qa(tokens: list[str], *, limit: int = 8) -> list[dict]:
    """Keyword-overlap search over article title/text for the AI assistant.

    Substring (ILIKE) matching is used instead of full-text search so that
    Hebrew prefixed word forms (e.g. "בכתבות" containing "כתבות") still match,
    without needing a stemmer. Falls back to the most recent articles when no
    tokens match anything, so aggregate-style questions still get context.
    """
    require_database_url()
    base_select = """
        SELECT
            a.article_id, a.source, a.title, a.primary_category, a.first_seen_at,
            LEFT(a.text, 300) AS snippet,
            agg.audience_mean, agg.audience_p85, agg.num_comments
        FROM articles a
        LEFT JOIN LATERAL (
            SELECT audience_mean, audience_p85, num_comments
            FROM article_comments_agg
            WHERE article_id = a.article_id
            ORDER BY analyzed_at DESC
            LIMIT 1
        ) agg ON TRUE
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            if tokens:
                # Each token contributes one (title_pattern, text_pattern) pair,
                # reused identically in both the WHERE clause and the score
                # expression in ORDER BY — so the same pattern list is bound twice.
                patterns = [f"%{tok}%" for tok in tokens]
                where_sql = " OR ".join("(a.title ILIKE %s OR a.text ILIKE %s)" for _ in patterns)
                score_sql = " + ".join(
                    "(CASE WHEN a.title ILIKE %s THEN 2 ELSE 0 END) + "
                    "(CASE WHEN a.text ILIKE %s THEN 1 ELSE 0 END)"
                    for _ in patterns
                )
                pair_params = [p for pattern in patterns for p in (pattern, pattern)]
                query = (
                    f"{base_select} WHERE {where_sql} "
                    f"ORDER BY ({score_sql}) DESC, a.first_seen_at DESC LIMIT %s"
                )
                cur.execute(query, pair_params + pair_params + [limit])
                columns = [desc[0] for desc in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]
                if rows:
                    return rows

            cur.execute(
                f"{base_select} ORDER BY a.first_seen_at DESC LIMIT %s",
                [limit],
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def count_articles(
    *,
    source: str | None = None,
    category: str | None = None,
    min_audience_mean: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    q: str | None = None,
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
    filter_sql, params = _common_filters(
        source=source, category=category, start_date=start_date, end_date=end_date
    )
    query += filter_sql
    if min_audience_mean is not None:
        query += " AND agg.audience_mean >= %s"
        params.append(min_audience_mean)
    if q:
        query += " AND (a.title ILIKE %s OR a.text ILIKE %s)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return int(cur.fetchone()[0])

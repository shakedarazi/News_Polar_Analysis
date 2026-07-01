"""Article classification persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from src.db.config import require_database_url
from src.db.connection import get_connection
from src.nlp.classify import ClassificationResult


def ensure_classification_schema() -> None:
    from src.db.migrations import apply_migrations

    require_database_url()
    apply_migrations()


def iter_articles_for_classification(
    *,
    missing_only: bool = True,
    limit: int | None = None,
) -> list[dict]:
    require_database_url()
    query = """
        SELECT article_id, source, title, text
        FROM articles
    """
    if missing_only:
        query += " WHERE primary_category IS NULL"
    query += " ORDER BY first_seen_at DESC"
    params: list = []
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def save_classification(article_id: str, result: ClassificationResult) -> None:
    require_database_url()
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET primary_category = %s,
                    category_confidence = %s,
                    category_rationale = %s,
                    classification_model = %s,
                    categorized_at = %s
                WHERE article_id = %s
                """,
                (
                    result.primary_category,
                    result.confidence,
                    result.rationale,
                    result.model,
                    now,
                    article_id,
                ),
            )


def classify_and_save_article(record: dict) -> ClassificationResult:
    """Classify a newly saved article and persist the label."""
    from src.nlp.classify import classify_article

    result = classify_article(
        title=record.get("title"),
        text=record["text"],
        source=record.get("source"),
    )
    save_classification(record["article_id"], result)
    return result


def maybe_classify_after_save(
    record: dict,
    *,
    enabled: bool = True,
) -> ClassificationResult | None:
    """
    Classify article after ingestion. Returns None if disabled or on failure.
    The article remains saved even when classification fails.
    """
    if not enabled:
        return None

    from src.nlp.openai_config import get_openai_api_key

    if not get_openai_api_key():
        print("  WARN: OPENAI_API_KEY not set — article saved without category")
        return None

    try:
        result = classify_and_save_article(record)
        print(
            f"  Category: {result.primary_category} "
            f"({result.confidence:.0%}) — {result.rationale}"
        )
        return result
    except Exception as exc:
        print(f"  WARN: classification failed ({exc}) — article saved without category")
        return None

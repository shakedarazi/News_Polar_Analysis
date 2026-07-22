"""Article AI-summary persistence.

summary_key_points and summary_entities are stored as JSON-encoded TEXT
(rather than a JSONB column) to match the plain-column style already used
throughout sql/schema.sql and sql/migrations/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from src.db.config import require_database_url
from src.db.connection import get_connection
from src.nlp.summarize import SummaryResult

_SUMMARY_COLUMNS = (
    "summary_text",
    "summary_key_points",
    "summary_topic",
    "summary_entities",
    "summary_sentiment",
    "summary_model",
    "summary_generated_at",
)


def _row_to_summary(row: dict) -> dict:
    return {
        "summary": row["summary_text"],
        "key_points": json.loads(row["summary_key_points"]) if row["summary_key_points"] else [],
        "topic": row["summary_topic"],
        "entities": json.loads(row["summary_entities"]) if row["summary_entities"] else [],
        "sentiment": row["summary_sentiment"],
        "model": row["summary_model"],
        "generated_at": row["summary_generated_at"],
    }


def get_article_for_summary(article_id: str) -> dict | None:
    """Fetch the article fields needed to read or generate its AI summary."""
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT article_id, source, title, text, {", ".join(_SUMMARY_COLUMNS)}
                FROM articles
                WHERE article_id = %s
                """,
                (article_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            columns = [d[0] for d in cur.description]
            return dict(zip(columns, row))


def get_summary(article_id: str) -> dict | None:
    """Return the stored summary, or None if the article has none yet.

    Distinct from "article not found" — callers should check
    get_article_for_summary()/404 separately when that distinction matters.
    """
    record = get_article_for_summary(article_id)
    if record is None or record["summary_text"] is None:
        return None
    return _row_to_summary(record)


def save_summary(article_id: str, result: SummaryResult) -> None:
    require_database_url()
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET summary_text = %s,
                    summary_key_points = %s,
                    summary_topic = %s,
                    summary_entities = %s,
                    summary_sentiment = %s,
                    summary_model = %s,
                    summary_generated_at = %s
                WHERE article_id = %s
                """,
                (
                    result.summary,
                    json.dumps(result.key_points, ensure_ascii=False),
                    result.topic or None,
                    json.dumps(result.entities, ensure_ascii=False),
                    result.sentiment,
                    result.model,
                    now,
                    article_id,
                ),
            )


def generate_and_save_summary(article_id: str) -> dict:
    """Generate (if missing) and return the AI summary for an article.

    Idempotent: an existing completed summary is returned as-is and the AI
    is never called again for it.
    """
    from src.nlp.summarize import summarize_article

    record = get_article_for_summary(article_id)
    if record is None:
        raise LookupError("Article not found")
    if record["summary_text"] is not None:
        return _row_to_summary(record)
    if not record.get("text") or not record["text"].strip():
        raise ValueError("Article has no content to summarize")

    result = summarize_article(
        title=record.get("title"),
        text=record["text"],
        source=record.get("source"),
    )
    save_summary(article_id, result)
    return get_summary(article_id)  # re-read for a single, consistent formatting path

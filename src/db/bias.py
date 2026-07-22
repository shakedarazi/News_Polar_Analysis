"""Article political-bias-estimate persistence (see src/nlp/bias.py)."""

from __future__ import annotations

from datetime import datetime, timezone

from src.db.config import require_database_url
from src.db.connection import get_connection
from src.nlp.bias import BiasResult

_BIAS_COLUMNS = (
    "bias_label",
    "bias_score",
    "bias_confidence",
    "bias_rationale",
    "bias_model",
    "bias_generated_at",
)


def _row_to_bias(row: dict) -> dict:
    return {
        "applicable": row["bias_label"] is not None,
        "label": row["bias_label"],
        "score": row["bias_score"],
        "confidence": row["bias_confidence"],
        "rationale": row["bias_rationale"],
        "model": row["bias_model"],
        "generated_at": row["bias_generated_at"],
    }


def get_article_for_bias(article_id: str) -> dict | None:
    """Fetch the article fields needed to read or generate its bias estimate."""
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT article_id, source, title, text, {", ".join(_BIAS_COLUMNS)}
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


def get_bias(article_id: str) -> dict | None:
    """Return the stored bias estimate, or None if it hasn't been generated yet.

    A generated-but-not-applicable result (bias_label is NULL, bias_generated_at
    is set) is still returned here — callers distinguish "missing" from
    "not applicable" via bias_generated_at, not via this function alone.
    """
    record = get_article_for_bias(article_id)
    if record is None or record["bias_generated_at"] is None:
        return None
    return _row_to_bias(record)


def save_bias(article_id: str, result: BiasResult) -> None:
    require_database_url()
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET bias_label = %s,
                    bias_score = %s,
                    bias_confidence = %s,
                    bias_rationale = %s,
                    bias_model = %s,
                    bias_generated_at = %s
                WHERE article_id = %s
                """,
                (
                    result.label,
                    result.score,
                    result.confidence,
                    result.rationale,
                    result.model,
                    now,
                    article_id,
                ),
            )


def generate_and_save_bias(article_id: str) -> dict:
    """Generate (if missing) and return the bias estimate for an article.

    Idempotent: once bias_generated_at is set (applicable or not), the AI is
    never called again for that article.
    """
    from src.nlp.bias import estimate_bias

    record = get_article_for_bias(article_id)
    if record is None:
        raise LookupError("Article not found")
    if record["bias_generated_at"] is not None:
        return _row_to_bias(record)
    if not record.get("text") or not record["text"].strip():
        raise ValueError("Article has no content to analyze")

    result = estimate_bias(
        title=record.get("title"),
        text=record["text"],
        source=record.get("source"),
    )
    save_bias(article_id, result)
    return get_bias(article_id)

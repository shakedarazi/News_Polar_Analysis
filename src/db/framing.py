"""Article framing-extraction persistence (see src/nlp/framing.py).

Same shape as src/db/bias.py: generated on demand from the API, cached in
columns on `articles`, and never regenerated once framing_generated_at is set.
Framing is enrichment — the deterministic pipeline must not depend on it and
must not treat its absence as an error.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.db.config import require_database_url
from src.db.connection import get_connection
from src.nlp.framing import FramingResult

_FRAMING_COLUMNS = (
    "framing_actor",
    "framing_actor_grounded",
    "framing_responsibility",
    "framing_loaded_terms",
    "framing_dropped_terms",
    "framing_voice",
    "framing_lead_perspective",
    "framing_model",
    "framing_generated_at",
)


def _row_to_framing(row: dict) -> dict:
    return {
        # A grounded actor only. The ungrounded one is reported separately so
        # the UI can show that the check fired without repeating the claim.
        "actor": row["framing_actor"] if row["framing_actor_grounded"] else None,
        "rejected_actor": None if row["framing_actor_grounded"] else row["framing_actor"],
        "responsibility": row["framing_responsibility"],
        "loaded_terms": list(row["framing_loaded_terms"] or []),
        "dropped_terms": list(row["framing_dropped_terms"] or []),
        "voice": row["framing_voice"],
        "lead_perspective": row["framing_lead_perspective"],
        "model": row["framing_model"],
        "generated_at": row["framing_generated_at"],
    }


def get_article_for_framing(article_id: str) -> dict | None:
    """Fetch the fields needed to read or generate an article's framing."""
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT article_id, source, title, text, {", ".join(_FRAMING_COLUMNS)}
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


def get_framing(article_id: str) -> dict | None:
    """Return the stored extraction, or None if it hasn't been generated yet."""
    record = get_article_for_framing(article_id)
    if record is None or record["framing_generated_at"] is None:
        return None
    return _row_to_framing(record)


def save_framing(article_id: str, result: FramingResult) -> None:
    require_database_url()
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE articles
                SET framing_actor = %s,
                    framing_actor_grounded = %s,
                    framing_responsibility = %s,
                    framing_loaded_terms = %s,
                    framing_dropped_terms = %s,
                    framing_voice = %s,
                    framing_lead_perspective = %s,
                    framing_model = %s,
                    framing_generated_at = %s
                WHERE article_id = %s
                """,
                (
                    result.actor,
                    result.actor_grounded,
                    result.responsibility,
                    result.loaded_terms,
                    result.dropped_terms,
                    result.voice,
                    result.lead_perspective,
                    result.model,
                    now,
                    article_id,
                ),
            )


def generate_and_save_framing(article_id: str) -> dict:
    """Generate (if missing) and return the framing extraction.

    Idempotent: once framing_generated_at is set the model is never called
    again for that article, including when the extraction came back empty.
    """
    from src.nlp.framing import extract_framing

    record = get_article_for_framing(article_id)
    if record is None:
        raise LookupError("Article not found")
    if record["framing_generated_at"] is not None:
        return _row_to_framing(record)
    if not record.get("text") or not record["text"].strip():
        raise ValueError("Article has no content to analyze")

    result = extract_framing(title=record.get("title"), text=record["text"])
    save_framing(article_id, result)
    return get_framing(article_id)

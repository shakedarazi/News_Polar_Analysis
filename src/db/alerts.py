"""Smart alert persistence.

Detection logic lives in src/analysis/alerts.py; this module only persists
detected candidates (deduplicated via dedup_key — see that module) and
serves the read/unread API. alert_id = sha256(dedup_key), the same
deterministic-id convention used for article_id (src/common/hashing.py).
"""

from __future__ import annotations

from src.common.hashing import sha256_hex
from src.db.config import require_database_url
from src.db.connection import get_connection


def detect_and_save_alerts() -> int:
    """Run all detectors and insert any newly-detected alerts.

    Returns the number of genuinely new alerts inserted (0 if everything
    detected already exists — this function is safe to call on every
    GET /api/alerts request).
    """
    from src.analysis.alerts import detect_all_alerts

    candidates = detect_all_alerts()
    if not candidates:
        return 0

    require_database_url()
    inserted = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for c in candidates:
                cur.execute(
                    """
                    INSERT INTO alerts (
                        alert_id, alert_type, severity, title, message,
                        related_article_id, related_event_id, related_topic,
                        related_source, link_path, dedup_key
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (dedup_key) DO NOTHING
                    """,
                    (
                        sha256_hex(c["dedup_key"]),
                        c["alert_type"],
                        c["severity"],
                        c["title"],
                        c["message"],
                        c.get("related_article_id"),
                        c.get("related_event_id"),
                        c.get("related_topic"),
                        c.get("related_source"),
                        c.get("link_path"),
                        c["dedup_key"],
                    ),
                )
                inserted += cur.rowcount
    return inserted


def list_alerts(
    *,
    alert_type: str | None = None,
    severity: str | None = None,
    limit: int = 30,
) -> list[dict]:
    require_database_url()
    query = """
        SELECT alert_id, alert_type, severity, title, message,
               related_article_id, related_event_id, related_topic,
               related_source, link_path, is_read, created_at
        FROM alerts
        WHERE 1=1
    """
    params: list = []
    if alert_type:
        query += " AND alert_type = %s"
        params.append(alert_type)
    if severity:
        query += " AND severity = %s"
        params.append(severity)
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, r)) for r in cur.fetchall()]


def count_unread() -> int:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM alerts WHERE is_read = FALSE")
            return int(cur.fetchone()[0])


def mark_read(alert_id: str) -> bool:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE alerts SET is_read = TRUE WHERE alert_id = %s", (alert_id,))
            return cur.rowcount > 0


def mark_all_read() -> int:
    require_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE alerts SET is_read = TRUE WHERE is_read = FALSE")
            return cur.rowcount

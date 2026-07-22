-- Smart alerts (idempotent). dedup_key encodes the alert condition + the
-- specific time window/entity it fired for, so re-running detection never
-- inserts a duplicate row for the same condition-instance (see
-- src/analysis/alerts.py for how each dedup_key is built).
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    related_article_id TEXT REFERENCES articles(article_id),
    related_event_id TEXT,
    related_topic TEXT,
    related_source TEXT,
    link_path TEXT,
    dedup_key TEXT NOT NULL UNIQUE,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON alerts (is_read);

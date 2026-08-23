-- Per-source crawl observability: one row per (run_id, source) so run
-- history is queryable without grepping log files.
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    saved INTEGER NOT NULL DEFAULT 0,
    skipped INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    crashed BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    PRIMARY KEY (run_id, source)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at ON ingestion_runs (started_at DESC);

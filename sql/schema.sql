CREATE TABLE IF NOT EXISTS articles (
    article_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    text TEXT NOT NULL,
    canonical_url TEXT NOT NULL UNIQUE,
    first_seen_at TIMESTAMPTZ NOT NULL,
    ingestion_run_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_source ON articles (source);
CREATE INDEX IF NOT EXISTS idx_articles_first_seen_at ON articles (first_seen_at);

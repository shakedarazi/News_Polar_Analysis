-- Comments scraped from news article pages
CREATE TABLE IF NOT EXISTS comments (
    comment_id TEXT PRIMARY KEY,
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    source TEXT NOT NULL,
    text TEXT NOT NULL,
    author TEXT,
    like_count INTEGER NOT NULL DEFAULT 0,
    published_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fetch_run_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_comments_article_id ON comments (article_id);
CREATE INDEX IF NOT EXISTS idx_comments_source ON comments (source);

ALTER TABLE articles ADD COLUMN IF NOT EXISTS comments_fetched_at TIMESTAMPTZ;

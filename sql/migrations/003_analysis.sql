-- Lexicon-based analysis results

ALTER TABLE articles ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS windows_features (
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    sentence_idx INTEGER NOT NULL,
    window_len INTEGER NOT NULL,
    c1 INTEGER NOT NULL DEFAULT 0,
    c2 INTEGER NOT NULL DEFAULT 0,
    c3 INTEGER NOT NULL DEFAULT 0,
    c4 INTEGER NOT NULL DEFAULT 0,
    c5 INTEGER NOT NULL DEFAULT 0,
    c6 INTEGER NOT NULL DEFAULT 0,
    c7 INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 0,
    dominance REAL,
    lexicon_version TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    run_id TEXT NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (article_id, sentence_idx, lexicon_version, pipeline_version)
);

CREATE TABLE IF NOT EXISTS comments_features (
    comment_id TEXT NOT NULL REFERENCES comments(comment_id),
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    comment_len INTEGER NOT NULL,
    polar_count INTEGER NOT NULL,
    polar_ratio REAL NOT NULL,
    like_count INTEGER NOT NULL DEFAULT 0,
    dislike_count INTEGER NOT NULL DEFAULT 0,
    engagement_weight REAL NOT NULL,
    comment_score REAL NOT NULL,
    controversy REAL NOT NULL,
    comment_lexicon_version TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    run_id TEXT NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (comment_id, comment_lexicon_version, pipeline_version)
);

CREATE TABLE IF NOT EXISTS article_comments_agg (
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    num_comments INTEGER NOT NULL,
    audience_mean REAL,
    audience_p85 REAL,
    controversy_mean REAL,
    controversy_p85 REAL,
    sum_engagement_weight REAL NOT NULL DEFAULT 0,
    comment_lexicon_version TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    run_id TEXT NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (article_id, comment_lexicon_version, pipeline_version)
);

CREATE INDEX IF NOT EXISTS idx_windows_features_article ON windows_features (article_id);
CREATE INDEX IF NOT EXISTS idx_comments_features_article ON comments_features (article_id);
CREATE INDEX IF NOT EXISTS idx_article_comments_agg_article ON article_comments_agg (article_id);

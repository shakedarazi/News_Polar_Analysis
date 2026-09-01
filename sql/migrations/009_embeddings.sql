-- Semantic event clustering: article title embeddings, and the cluster id
-- derived from them.
--
-- Re-applied on every init_db.py run and every API startup (there is no
-- migration version table), so everything here is written to be a no-op the
-- second time.

-- pgvector ships with Neon and with the Postgres 16 image used locally, but it
-- is not enabled by default on a fresh database.
CREATE EXTENSION IF NOT EXISTS vector;

-- 384 dimensions = intfloat/multilingual-e5-small, the model the embedding
-- pipeline pins. A different model means a different dimension, which would
-- fail loudly here rather than silently mixing two vector spaces in one column.
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS title_embedding vector(384),
    ADD COLUMN IF NOT EXISTS embedding_model TEXT,
    ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ,
    -- The persisted cluster id. Until the first embedding run this is NULL for
    -- every row, and event detection falls back to the lexical grouping in
    -- src/analysis/event_grouping.py.
    ADD COLUMN IF NOT EXISTS event_id TEXT,
    ADD COLUMN IF NOT EXISTS event_assigned_at TIMESTAMPTZ;

-- The embedding pass's work queue: articles with a category (the only ones
-- clustering considers) that have no vector yet, or carry one from a different
-- model.
CREATE INDEX IF NOT EXISTS idx_articles_needs_embedding
    ON articles (first_seen_at)
    WHERE title_embedding IS NULL AND primary_category IS NOT NULL;

-- Event reads go id -> members, so the id is the leading column.
CREATE INDEX IF NOT EXISTS idx_articles_event_id
    ON articles (event_id)
    WHERE event_id IS NOT NULL;

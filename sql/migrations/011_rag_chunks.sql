-- Retrieval passages for the assistant: one row per chunk of one article.
--
-- Re-applied on every init_db.py run and every API startup (there is no
-- migration version table), so everything here is written to be a no-op the
-- second time.
--
-- Why a table and not more columns on `articles`: an article has many chunks,
-- and the whole point of the split is that retrieval scores a paragraph rather
-- than a document. See src/rag/chunking.py.

CREATE EXTENSION IF NOT EXISTS vector;

-- Trigram matching for the lexical half of the search. Hebrew has no Postgres
-- stemmer, and full-text search on the 'simple' config would miss every
-- prefixed form — "בכתבות" would not match "כתבות" — which is the same reason
-- src/db/browse.py reaches for ILIKE rather than tsvector. Trigrams match
-- inside a word, so the prefixes cost nothing, and unlike a bare ILIKE they
-- can be indexed.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS article_chunks (
    chunk_id        TEXT PRIMARY KEY,
    -- ON DELETE CASCADE: a chunk has no meaning without its article, and
    -- nothing else references it.
    article_id      TEXT NOT NULL REFERENCES articles(article_id) ON DELETE CASCADE,
    ordinal         INTEGER NOT NULL,
    text            TEXT NOT NULL,
    -- 512 dimensions = text-embedding-3-small truncated per src/rag/embedding.py.
    -- NULL until the embedding pass reaches this row; the row is written during
    -- ingestion by the chunking pass, which needs no API key.
    embedding       vector(512),
    embedding_model TEXT,
    embedded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- One chunk per (article, position). Makes re-chunking an upsert rather
    -- than a delete-and-insert, so a re-run cannot leave an article with two
    -- generations of chunks half-visible to a concurrent reader.
    UNIQUE (article_id, ordinal)
);

-- The semantic channel. HNSW rather than IVFFlat: it needs no training step and
-- no rebuild as rows arrive, which matters for a table that grows every six
-- hours. vector_cosine_ops matches the `<=>` operator the search uses.
--
-- Built on a partial predicate so unembedded rows stay out of the index.
CREATE INDEX IF NOT EXISTS idx_article_chunks_embedding
    ON article_chunks USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

-- The lexical channel: GIN over trigrams, which is what makes an
-- unanchored ILIKE '%term%' an index scan instead of a sequential one.
CREATE INDEX IF NOT EXISTS idx_article_chunks_text_trgm
    ON article_chunks USING gin (text gin_trgm_ops);

-- The chunking pass's work queue, and the join back to the article.
CREATE INDEX IF NOT EXISTS idx_article_chunks_article
    ON article_chunks (article_id);

-- Rows written but not yet embedded.
CREATE INDEX IF NOT EXISTS idx_article_chunks_needs_embedding
    ON article_chunks (created_at)
    WHERE embedding IS NULL;

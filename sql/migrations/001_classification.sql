-- Add AI classification columns to articles (idempotent)
ALTER TABLE articles ADD COLUMN IF NOT EXISTS primary_category TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS category_confidence REAL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS category_rationale TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS classification_model TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS categorized_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_articles_primary_category ON articles (primary_category);

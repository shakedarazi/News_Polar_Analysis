-- AI-generated article summaries (idempotent)
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_text TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_key_points TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_topic TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_entities TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_sentiment TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_model TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_generated_at TIMESTAMPTZ;

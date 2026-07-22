-- AI-estimated political framing/bias per article (idempotent).
-- Distinct from lexicon polarity (article_comments_agg/windows_features) and
-- from summary_sentiment (src/nlp/summarize.py) — bias_label is never derived
-- from either. bias_label is NULL when the article has no clear political
-- framing (e.g. sports/weather), even after generation has run once.
ALTER TABLE articles ADD COLUMN IF NOT EXISTS bias_label TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS bias_score REAL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS bias_confidence REAL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS bias_rationale TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS bias_model TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS bias_generated_at TIMESTAMPTZ;

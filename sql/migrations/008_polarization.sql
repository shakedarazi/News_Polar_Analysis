-- Two-axis (Simchon) polarization scoring, stored beside the single-axis score.
-- See docs/adr/0004: the two readings share a denominator and a like weighting,
-- share 15% of their vocabulary, and are never blended into one number.
--
-- Every column is nullable with no default on purpose. NULL means this pass has
-- not run for that row yet; 0 means it ran and found no lexicon word. Roughly
-- 50k comments were scored before these columns existed, and a DEFAULT 0 would
-- have made them indistinguishable from genuinely unpolarized comments — the
-- same reason windows_features.dominance is nullable.
--
-- Re-applied on every init_db.py run and API startup (there is no migration
-- version table), so every statement here must be safe to re-run.

ALTER TABLE comments_features
    ADD COLUMN IF NOT EXISTS issue_count INTEGER,
    ADD COLUMN IF NOT EXISTS affective_count INTEGER,
    ADD COLUMN IF NOT EXISTS issue_ratio REAL,
    ADD COLUMN IF NOT EXISTS affective_ratio REAL,
    ADD COLUMN IF NOT EXISTS polarization_lexicon_version TEXT;

ALTER TABLE article_comments_agg
    ADD COLUMN IF NOT EXISTS audience_issue_mean REAL,
    ADD COLUMN IF NOT EXISTS audience_affective_mean REAL,
    ADD COLUMN IF NOT EXISTS audience_issue_p85 REAL,
    ADD COLUMN IF NOT EXISTS audience_affective_p85 REAL,
    ADD COLUMN IF NOT EXISTS polarization_lexicon_version TEXT;

-- Answers "which articles still need the polarization pass" without scanning
-- the whole table once most rows are scored.
CREATE INDEX IF NOT EXISTS idx_article_comments_agg_needs_polarization
    ON article_comments_agg (article_id)
    WHERE polarization_lexicon_version IS NULL;

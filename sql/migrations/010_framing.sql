-- Media-framing variables per article, and the verifier's trace (src/nlp/framing.py).
--
-- Re-applied on every init_db.py run and every API startup (there is no
-- migration version table), so every statement here is a no-op the second time.
--
-- Distinct from bias_* (which camp the language leans to) and from
-- summary_sentiment (tone). Framing is structural: who acts, who is held
-- responsible, active or passive, whose point of view opens the piece.
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS framing_actor TEXT,
    -- FALSE means the extractor named an actor that does not occur in the
    -- text it was given. The value is kept so the rejection can be shown;
    -- readers must gate display on this column, never on framing_actor alone.
    ADD COLUMN IF NOT EXISTS framing_actor_grounded BOOLEAN,
    ADD COLUMN IF NOT EXISTS framing_responsibility TEXT,
    -- Only terms that survived grounding against the headline + lead.
    ADD COLUMN IF NOT EXISTS framing_loaded_terms TEXT[],
    -- Terms the verifier rejected. Empty is the normal case; this is evidence
    -- the check ran, not an error log.
    ADD COLUMN IF NOT EXISTS framing_dropped_terms TEXT[],
    ADD COLUMN IF NOT EXISTS framing_voice TEXT,
    ADD COLUMN IF NOT EXISTS framing_lead_perspective TEXT,
    ADD COLUMN IF NOT EXISTS framing_model TEXT,
    -- The "has run" marker. An extraction that produced nothing but nulls is
    -- still a completed extraction, so absence of this timestamp — not absence
    -- of framing_actor — is what means "not generated yet".
    ADD COLUMN IF NOT EXISTS framing_generated_at TIMESTAMPTZ;

-- active/passive is the only closed vocabulary in the set; anything else is a
-- parsing bug rather than a model opinion, and should fail on write.
ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_framing_voice_check;
ALTER TABLE articles
    ADD CONSTRAINT articles_framing_voice_check
    CHECK (framing_voice IS NULL OR framing_voice IN ('active', 'passive'));

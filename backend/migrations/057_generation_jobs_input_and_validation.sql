-- 057: what the merchant asked for, and what the checks said about what
-- they got.
--
-- Three runs produced three different corruptions of merchant input — an
-- item vanished (katering, "Pakej Doa Selamat"), an item was overwritten by
-- a duplicate of another (mkl, "Udang Bakar RM55" shipped as "Sotong Bakar
-- RM55"), and an address from an earlier session leaked in (site B) — and
-- none of them could be PROVEN afterwards, because the only thing this
-- table kept was the free-text description. The item list, the colour mode,
-- the style and the feature toggles all existed for the length of one
-- request and were then gone.
--
-- input_payload is that request, minus anything bulky or secret: it is the
-- ground truth every post-generation check is measured against, and the
-- only way a report like "item 4 came back wrong" can be settled rather
-- than argued.
--
-- validation is what generation_validator said about the output. It was
-- already computed on every generation and already logged; it was never
-- stored, so "the page shipped with a known defect" was invisible to
-- everything except a log search.
--
-- Both are additive and nullable: rows written before this migration stay
-- valid, and code that does not know about these columns is unaffected.

ALTER TABLE generation_jobs
    ADD COLUMN IF NOT EXISTS input_payload jsonb,
    ADD COLUMN IF NOT EXISTS validation    jsonb;

COMMENT ON COLUMN generation_jobs.input_payload IS
    'The merchant-supplied request this job was generated from (menu_items, '
    'color_mode, design_style, features, language…). Secrets, base64 images '
    'and uploaded image blobs are stripped before it is written.';

COMMENT ON COLUMN generation_jobs.validation IS
    'generation_validator result for the delivered HTML: {ok, model, errors, '
    'warnings}. needs_manual_review is set when errors survive the one '
    'repair attempt.';

-- Finding a flagged run is the point, so make that query cheap.
CREATE INDEX IF NOT EXISTS idx_generation_jobs_needs_review
    ON generation_jobs (created_at DESC)
    WHERE needs_manual_review = true;

-- Migration 055: Persist the merchant's vertical and hero-visual intent
--
-- Background: websites.business_type has existed since the schema was first
-- written, and was EMPTY ('') on every row ever created — 205/205 at the time
-- of this migration. The create page always sent the merchant's pick, but
-- /api/generate/start never read the key and the AI request hardcoded
-- business_type="business", so nothing ever wrote a real value. With no
-- persisted vertical, every downstream decision (image prompts, gallery card
-- names, order-button labels, category sets) fell back to keyword-guessing
-- the free-text description. A single incidental word was enough to flip a
-- vertical: a hair salon whose description mentioned customers enjoying
-- "kopi" was classified as a drinks business and shipped with a hero image of
-- iced beverages.
--
-- Columns:
--   business_type      — already present; this migration only documents it
--                        and adds the CHECK + index now that it carries real
--                        values. '' stays legal so the 205 historical rows
--                        remain valid: they are NOT backfilled, because the
--                        only thing available to backfill them with is the
--                        classifier that caused the bug. Those sites get a
--                        real value when they are next regenerated with an
--                        explicit type.
--   hero_image_prompt  — the merchant's own description of the hero VISUAL.
--                        Nullable; NULL means "auto-build from the vertical".
--                        Persisted so the prompt that produced a given hero
--                        can be read back off the row instead of being
--                        reconstructed by re-running generation. Distinct
--                        from the hero VIDEO prompt, which describes motion
--                        applied to this image afterwards and is not stored
--                        here.
--
-- Backward compatibility: business_type keeps its existing default; the new
-- column is nullable. Existing INSERTs and reads are unaffected.

ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS hero_image_prompt TEXT;

-- '' is the historical "never written" value and must remain accepted.
-- Anything else must be one of the canonical verticals in
-- app/services/business_types.py::BUSINESS_TYPE_VALUES.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'websites_business_type_check'
  ) THEN
    ALTER TABLE public.websites
      ADD CONSTRAINT websites_business_type_check
      CHECK (
        business_type IS NULL
        OR business_type IN (
          '', 'food', 'clothing', 'salon', 'services', 'bakery', 'general'
        )
      )
      NOT VALID;  -- NOT VALID: accept the legacy rows without a table rewrite.
  END IF;
END $$;

-- Powers "how many sites per vertical" analytics and, more importantly, lets
-- us find the rows still carrying the empty legacy value.
CREATE INDEX IF NOT EXISTS idx_websites_business_type
  ON public.websites(business_type);

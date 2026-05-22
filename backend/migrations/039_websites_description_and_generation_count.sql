-- Migration 039: Persist the AI generation description + regeneration counter
--
-- Background: Until now, the user's free-text description (the actual prompt
-- sent to DeepSeek) was discarded after the initial generation. Users who
-- wanted to "try again with a tweaked prompt" had to redo the entire create
-- flow (subdomain, business name, integrations, etc.) — the regenerate
-- workflow needs the original description to be persisted on the website
-- row so it can re-run generation in-place.
--
-- Columns:
--   description       — the natural-language prompt the user supplied.
--                       Nullable so historical rows that pre-date this
--                       migration aren't broken; the regenerate endpoint
--                       requires a non-null value (either the stored one
--                       or one the caller passes in the PATCH body).
--   generation_count  — number of times this website's HTML has been
--                       (re)generated. Defaults to 0 so legacy rows
--                       report 0 generations and the next regenerate
--                       increments to 1; the create endpoint sets this
--                       to 1 on initial create.
--
-- Backward compatibility: both columns are nullable / have defaults, so
-- existing INSERTs and reads keep working.

ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS description TEXT;

ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS generation_count INTEGER NOT NULL DEFAULT 0;

-- Useful for the dashboard "regenerated N times" badge and for analytics
-- queries that want to find high-churn sites.
CREATE INDEX IF NOT EXISTS idx_websites_generation_count
  ON public.websites(generation_count);

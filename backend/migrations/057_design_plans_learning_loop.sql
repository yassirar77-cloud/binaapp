-- Migration 057: design_plans — the learning loop for designer-grade generation
--
-- Background: website generation now runs in two passes. Pass 1 writes a
-- design PLAN (direction from the library, palette, type pairing, hero
-- treatment, signature element) and Pass 2 builds the HTML against it. Two
-- things need to survive the request:
--
--   1. The rolling direction history per category. Two sites of the same
--      vertical generated in a row must not share a direction, so Pass 1
--      reads the last three directions used for that vertical and excludes
--      them. Without a table the exclusion only worked inside one process.
--
--   2. What each plan produced and what the merchant did with it. The
--      weekly direction-stats job (app/cron/design_stats_cron.py) reads
--      publish / edit / regenerate outcomes per direction and flags the
--      directions with the lowest publish rate in
--      docs/design/direction-stats.md so the library can be tuned on
--      evidence rather than taste.
--
-- One row per generation attempt. website_id is nullable because the plan
-- is recorded before the draft website row exists (job path) and stamped
-- afterwards; job_id ties the two together.
--
-- Outcome values: generated (default), published, edited, regenerated,
-- discarded. Written best-effort from the publish and regenerate paths;
-- a missing row never blocks a publish.

CREATE TABLE IF NOT EXISTS public.design_plans (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id          TEXT,
  website_id      UUID,
  user_id         TEXT,
  category        TEXT NOT NULL DEFAULT 'general',
  direction       TEXT NOT NULL,
  plan            JSONB NOT NULL,
  plan_source     TEXT NOT NULL DEFAULT 'ai',        -- ai | fallback
  critique        JSONB,                             -- scores per rubric criterion + notes
  critique_avg    NUMERIC(4,2),
  lint            JSONB,                             -- anti-template lint report
  html_sha256     TEXT,
  attempts        INTEGER NOT NULL DEFAULT 1,
  outcome         TEXT NOT NULL DEFAULT 'generated', -- generated | published | edited | regenerated | discarded
  outcome_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The rolling-history read: "last 3 plans for this category, newest first".
CREATE INDEX IF NOT EXISTS idx_design_plans_category_created
  ON public.design_plans(category, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_design_plans_website
  ON public.design_plans(website_id);

CREATE INDEX IF NOT EXISTS idx_design_plans_job
  ON public.design_plans(job_id);

-- Service-role only: the backend reads and writes this table; there is no
-- merchant-facing surface for it.
ALTER TABLE public.design_plans ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'design_plans' AND policyname = 'design_plans_service_role_all'
  ) THEN
    CREATE POLICY design_plans_service_role_all ON public.design_plans
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

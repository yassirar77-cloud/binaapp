-- ==========================================================================
-- Migration 071: mascot_videos — a merchant's clip with a mascot added
-- ==========================================================================
-- WHY
-- Mascot Video (MASCOT_VIDEO_ENABLED, off by default): a merchant uploads a
-- 2–10 s clip of their shop or food and a mascot image, and wan3.0-video
-- (DashScope) edits the mascot into the real scene. Every attempt is a row:
-- what was uploaded, what was asked, where it went (provider task id), what
-- came back and what it cost. The per-merchant daily cap
-- (MASCOT_VIDEO_DAILY_LIMIT) is counted from rows that reached the provider.
--
-- status: queued → moderating → processing → ready | rejected | failed
--   rejected = Qwen moderation refused the clip; nothing was rendered.
--
-- ACCESS
-- Merchants may READ their own rows (RLS: merchant_id = auth.uid()). All
-- writes go through the backend with the service role, which is where the
-- flag, the consent check, moderation and the daily cap are enforced — so
-- there is deliberately no INSERT/UPDATE/DELETE policy for merchants.
--
-- Files live in the private `mascot-videos` bucket under unguessable keys
-- and are streamed out by the backend (/api/v1/mascot-videos/media/<key>).
--
-- Additive and idempotent; safe to re-run.
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.mascot_videos (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    clip_url         TEXT NOT NULL,                    -- the uploaded clip
    mascot_url       TEXT NOT NULL,                    -- the mascot image
    prompt           TEXT NOT NULL DEFAULT '',         -- what the merchant asked the mascot to do
    status           TEXT NOT NULL DEFAULT 'queued'
                     CHECK (status IN ('queued', 'moderating', 'processing', 'ready', 'rejected', 'failed')),
    result_url       TEXT,                             -- the finished clip (NULL until ready)
    cost             NUMERIC(10,4) NOT NULL DEFAULT 0, -- USD: estimate at submit, metered when ready
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- bookkeeping
    clip_key         TEXT NOT NULL,                    -- object keys in the mascot-videos bucket
    mascot_key       TEXT NOT NULL,
    result_key       TEXT,
    clip_seconds     NUMERIC(6,2) NOT NULL DEFAULT 0,
    resolution       TEXT NOT NULL DEFAULT '720P',
    model            TEXT,                             -- wan3.0-video
    task_id          TEXT,                             -- provider task id (NULL = never rendered)
    provider_status  TEXT,
    error            TEXT,
    consent_at       TIMESTAMPTZ NOT NULL,             -- merchant confirmed people in the clip agreed
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at      TIMESTAMPTZ
);

COMMENT ON TABLE public.mascot_videos IS
  'Mascot Video jobs: a merchant clip edited by wan3.0-video (DashScope) to include a mascot. Drives the job status, the cost log and the per-merchant daily cap.';

CREATE INDEX IF NOT EXISTS idx_mascot_videos_merchant_created
  ON public.mascot_videos(merchant_id, created_at DESC);

ALTER TABLE public.mascot_videos ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'mascot_videos' AND policyname = 'mascot_videos_select_own'
  ) THEN
    CREATE POLICY mascot_videos_select_own ON public.mascot_videos
      FOR SELECT TO authenticated
      USING (merchant_id = (SELECT auth.uid()));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'mascot_videos' AND policyname = 'mascot_videos_service_role_all'
  ) THEN
    CREATE POLICY mascot_videos_service_role_all ON public.mascot_videos
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

-- Merchants read only; anon gets nothing.
REVOKE ALL ON public.mascot_videos FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mascot_videos FROM authenticated;
GRANT SELECT ON public.mascot_videos TO authenticated;

-- Private bucket for clips, mascots and results.
INSERT INTO storage.buckets (id, name, public)
VALUES ('mascot-videos', 'mascot-videos', false)
ON CONFLICT (id) DO NOTHING;

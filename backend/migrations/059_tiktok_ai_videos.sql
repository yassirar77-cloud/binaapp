-- ==========================================================================
-- Migration 059: tiktok_ai_videos — AI promo clips made for TikTok posts
-- ==========================================================================
-- WHY
-- /admin/tiktok can now make a vertical promo clip from 1–3 real photos and
-- a short brief with the existing Wan 3.0 (DashScope) image/reference-to-
-- video integration, then post it through the TikTok flow. Each generation
-- costs real money, so every attempt is a row: what was asked (brief,
-- prompt, photos, resolution, duration), where it went (provider task id),
-- what came back (video key in the private tiktok-media bucket), and what
-- it cost. The admin page shows this as the cost log, and the daily cap
-- (WAN_DAILY_VIDEO_LIMIT) is counted from rows that reached the provider.
--
-- status: queued → processing → ready | failed
--
-- Service-role only, like the other tiktok_* tables (migration 058).
-- Additive and idempotent; safe to re-run.
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.tiktok_ai_videos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by          TEXT NOT NULL,                    -- admin user id
    brief               TEXT NOT NULL DEFAULT '',
    prompt              TEXT NOT NULL DEFAULT '',         -- exactly what the provider received
    photo_keys          JSONB NOT NULL DEFAULT '[]'::jsonb, -- reference photos in tiktok-media
    resolution          TEXT NOT NULL DEFAULT '720P',     -- 480P | 720P | 1080P
    duration_sec        INTEGER NOT NULL DEFAULT 10,
    aspect              TEXT NOT NULL DEFAULT '9:16',
    provider            TEXT,                             -- dashscope
    model               TEXT,                             -- wan3.0-video
    task_id             TEXT,                             -- provider task id (NULL = never submitted)
    status              TEXT NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued', 'processing', 'ready', 'failed')),
    provider_status     TEXT,
    error               TEXT,
    video_key           TEXT,                             -- <uuid>.mp4 in tiktok-media
    video_bytes         BIGINT,
    estimated_cost_usd  NUMERIC(10,4) NOT NULL DEFAULT 0,
    estimated_cost_rm   NUMERIC(10,2) NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ
);

COMMENT ON TABLE public.tiktok_ai_videos IS
  'Ledger of AI promo clips (Wan 3.0 via DashScope) generated for TikTok posts from the admin dashboard; drives the cost log and the daily cap.';

CREATE INDEX IF NOT EXISTS idx_tiktok_ai_videos_created
  ON public.tiktok_ai_videos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tiktok_ai_videos_status
  ON public.tiktok_ai_videos(status);

ALTER TABLE public.tiktok_ai_videos ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'tiktok_ai_videos' AND policyname = 'tiktok_ai_videos_service_role_all'
  ) THEN
    CREATE POLICY tiktok_ai_videos_service_role_all ON public.tiktok_ai_videos
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

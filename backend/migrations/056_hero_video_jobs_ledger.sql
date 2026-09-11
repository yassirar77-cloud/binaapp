-- ==========================================================================
-- Migration 056: hero-video job ledger + the video on the websites row
-- ==========================================================================
-- WHY
-- Hero-video jobs lived only in process memory (zai_video_service._jobs).
-- Render redeploys the backend on every push (eight times on 2026-09-10);
-- each restart forgot every job that was still rendering or was stored and
-- waiting to be published. The provider finished the clip, nobody collected
-- it, nothing was logged, the stuck sweep (which only looks at
-- websites.status='generating') could not see it, and a paid credit was
-- never refunded. Separately, nothing on the websites row ever recorded
-- which clip a site carries — the URL existed only inside html_content, so
-- a regeneration silently dropped it and there was nothing to reconcile from.
--
-- WHAT
--   hero_video_jobs          one row per job, written at every state change.
--                            On startup the backend resumes every row that is
--                            not terminal; the stuck sweep fails rows that
--                            exceeded the hard timeout, regardless of the
--                            website's own status.
--   websites.hero_video_*    the clip the site is supposed to carry. Written
--                            BEFORE the HTML is patched, cleared on removal.
--
-- Service-role only: the backend writes with the service key (bypasses RLS);
-- RLS is enabled with no policies so anon/authenticated roles see nothing.
-- Additive and idempotent; safe to re-run.
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.hero_video_jobs (
    job_id            TEXT PRIMARY KEY,
    task_id           TEXT NOT NULL,
    provider          TEXT NOT NULL,
    -- TEXT, not UUID + FK: a prepared job has no site yet, and deleting a
    -- site must not erase the ledger entry that says a credit was spent.
    website_id        TEXT NOT NULL DEFAULT '',
    user_id           TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN (
                          'processing', 'storing', 'ready', 'completed', 'failed'
                      )),
    error             TEXT,
    -- Raw provider state from the last poll (PENDING / RUNNING / SUCCEEDED /
    -- FAILED / …) or http_<code> when the poll itself failed.
    provider_status   TEXT,
    provider_message  TEXT,
    prompt            TEXT NOT NULL DEFAULT '',
    image_url         TEXT,
    settings          JSONB NOT NULL DEFAULT '{}'::jsonb,
    video_url         TEXT,
    poster_url        TEXT,
    charged           BOOLEAN NOT NULL DEFAULT FALSE,
    refunded          BOOLEAN NOT NULL DEFAULT FALSE,
    applied           BOOLEAN NOT NULL DEFAULT FALSE,
    live_site_updated BOOLEAN NOT NULL DEFAULT FALSE,
    poll_errors       INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_polled_at    TIMESTAMPTZ,
    finished_at       TIMESTAMPTZ
);

COMMENT ON TABLE public.hero_video_jobs IS
    'Durable ledger of hero-video generation jobs. Source of truth for '
    'restart recovery and the stuck sweep; the in-memory registry is a cache.';

CREATE INDEX IF NOT EXISTS idx_hero_video_jobs_status
    ON public.hero_video_jobs(status);
CREATE INDEX IF NOT EXISTS idx_hero_video_jobs_website
    ON public.hero_video_jobs(website_id);
CREATE INDEX IF NOT EXISTS idx_hero_video_jobs_created
    ON public.hero_video_jobs(created_at);

ALTER TABLE public.hero_video_jobs ENABLE ROW LEVEL SECURITY;

-- The clip a published site carries. NULL = no video.
ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS hero_video_url TEXT,
  ADD COLUMN IF NOT EXISTS hero_video_poster_url TEXT,
  ADD COLUMN IF NOT EXISTS hero_video_settings JSONB,
  ADD COLUMN IF NOT EXISTS hero_video_updated_at TIMESTAMPTZ;

COMMENT ON COLUMN public.websites.hero_video_url IS
    'Cloudinary delivery URL of the hero background clip the site should '
    'carry. Written before the HTML is patched; NULL after removal.';

-- Ownership. Render overlaps the old and new instance during a deploy, so
-- two processes can hold the same job. A row is driven only by the process
-- whose lease is current; a restart or the sweep adopts rows whose lease
-- has lapsed (the process that held them is gone), via a conditional
-- PATCH that only one caller can win.
ALTER TABLE public.hero_video_jobs
  ADD COLUMN IF NOT EXISTS lease_owner TEXT,
  ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_hero_video_jobs_lease
    ON public.hero_video_jobs(lease_until);

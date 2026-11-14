-- Migration 067: marketing attribution for binaapp.my itself
--
-- Answers two questions the founder could not answer before:
--   1. How many people reach binaapp.my, and from where?  (marketing_visits_daily)
--   2. Which source did each signup come from?             (profiles.signup_*)
--
-- Privacy (same stance as migration 050):
--   * No visitor id, IP or user agent is stored. The browser pings at most
--     once per day, so `visits` approximates daily unique browsers.
--   * Only a short, normalised source label is kept ("tiktok", "google",
--     "whatsapp", "direct", a utm_source value, or a bare referrer domain).
--   * Visitors sending DNT / Global Privacy Control are never counted.
--
-- Backend/service-role only: RLS is on with no policies.
-- Idempotent: safe to run more than once.

-- ---------------------------------------------------------------------------
-- A. Where each signup came from (first touch)
-- ---------------------------------------------------------------------------
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS signup_source       TEXT,
    ADD COLUMN IF NOT EXISTS signup_medium       TEXT,
    ADD COLUMN IF NOT EXISTS signup_campaign     TEXT,
    ADD COLUMN IF NOT EXISTS signup_content      TEXT,
    ADD COLUMN IF NOT EXISTS signup_referrer     TEXT,
    ADD COLUMN IF NOT EXISTS signup_landing_path TEXT;

COMMENT ON COLUMN public.profiles.signup_source IS
    'First-touch marketing source at signup (tiktok, google, whatsapp, direct, utm_source, or referrer domain). NULL for accounts created before migration 067.';

-- ---------------------------------------------------------------------------
-- B. Daily visits to binaapp.my by source
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.marketing_visits_daily (
    date      DATE NOT NULL,
    source    TEXT NOT NULL DEFAULT 'direct',
    medium    TEXT NOT NULL DEFAULT '',
    campaign  TEXT NOT NULL DEFAULT '',
    visits    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, source, medium, campaign)
);

ALTER TABLE public.marketing_visits_daily ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.marketing_visits_daily FROM anon, authenticated;
GRANT ALL ON public.marketing_visits_daily TO service_role;

COMMENT ON TABLE public.marketing_visits_daily IS
    'Daily visits to binaapp.my by marketing source. Counters only, no visitor identifiers. Backend-only; see migration 067.';

-- ---------------------------------------------------------------------------
-- C. Atomic increment
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.track_marketing_visit(
    p_date DATE,
    p_source TEXT,
    p_medium TEXT,
    p_campaign TEXT
) RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    INSERT INTO marketing_visits_daily AS m (date, source, medium, campaign, visits)
    VALUES (
        p_date,
        COALESCE(NULLIF(p_source, ''), 'direct'),
        COALESCE(p_medium, ''),
        COALESCE(p_campaign, ''),
        1
    )
    ON CONFLICT (date, source, medium, campaign)
    DO UPDATE SET visits = m.visits + 1;
$$;

REVOKE ALL ON FUNCTION public.track_marketing_visit(DATE, TEXT, TEXT, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.track_marketing_visit(DATE, TEXT, TEXT, TEXT)
    TO service_role;

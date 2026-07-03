-- =============================================================================
-- Migration 050: PDPA-safe visitor analytics (rollup-only) + legacy IP purge
-- =============================================================================
--
-- WHAT THIS SHIPS
--   A cookieless, PDPA-compliant visitor-analytics pipeline for the merchant
--   "Analitik" dashboard:
--     * site_analytics_daily            — per-website daily counters
--     * site_analytics_pages_daily      — per-website daily top-page counters
--     * site_analytics_referrers_daily  — per-website daily referrer counters
--     * site_analytics_visitors_daily   — per-(website, day, visitor_hash)
--                                         dedup rows used ONLY to count uniques
--     * track_site_pageview(...)        — atomic write-time rollup RPC
--     * cleanup_analytics_visitor_hashes(...) — dedup-row retention purge
--
-- DESIGN: ROLLUP-ONLY, NO RAW EVENTS
--   Unlike the legacy `analytics` table, NO per-event rows are stored. Every
--   read the dashboard needs (views, uniques, top pages, referrer sources,
--   device split) is a daily counter maintained atomically at write time, so
--   reads never touch raw events — there are none. Trade-off (accepted): a
--   dimension not counted below (e.g. browser split) cannot be backfilled for
--   past days; add a new counter table and it accrues from that day forward.
--
-- PDPA / PRIVACY PROPERTIES
--   * No IP address and no user agent are ever stored (the backend uses them
--     transiently, in memory only, to compute visitor_hash).
--   * visitor_hash = sha256(secret_salt | YYYY-MM-DD (Asia/Kuala_Lumpur) | ip
--     | user_agent | website_id) — salted and DAILY-ROTATING, so hashes from
--     different days are unlinkable and cross-site tracking is impossible.
--   * Dedup rows are purged after 2 days (cleanup_analytics_visitor_hashes,
--     called daily by the backend scheduler), closing even the
--     salt-plus-recompute window.
--   * DNT / Sec-GPC are honoured in the tracking snippet AND the endpoint;
--     nothing here is reached for those visitors.
--   * Section E below also purges historical raw IPs from the legacy table.
--
-- HOW TO APPLY
--   This file is committed but NOT auto-applied (no migration runner in CI).
--   Run it in the Supabase SQL editor. It is idempotent — safe to re-run.
-- =============================================================================

BEGIN;

-- =============================================================================
-- SECTION A — rollup tables (website_id UUID-keyed, unlike the legacy
--             hostname-keyed analytics tables)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.site_analytics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_views INTEGER NOT NULL DEFAULT 0,
    unique_visitors INTEGER NOT NULL DEFAULT 0,
    mobile_views INTEGER NOT NULL DEFAULT 0,
    tablet_views INTEGER NOT NULL DEFAULT 0,
    desktop_views INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (website_id, date)
);

CREATE TABLE IF NOT EXISTS public.site_analytics_pages_daily (
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    -- Normalized by the backend: path only (query string stripped), <= 200 chars
    page_path TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (website_id, date, page_path)
);

CREATE TABLE IF NOT EXISTS public.site_analytics_referrers_daily (
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    -- Normalized by the backend: bare domain ('google.com') or 'direct'
    referrer_source TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (website_id, date, referrer_source)
);

-- Dedup rows for unique-visitor counting ONLY. No IP, no UA, hash rotates
-- daily. Purged after 2 days by cleanup_analytics_visitor_hashes().
CREATE TABLE IF NOT EXISTS public.site_analytics_visitors_daily (
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    visitor_hash TEXT NOT NULL,
    PRIMARY KEY (website_id, date, visitor_hash)
);

CREATE INDEX IF NOT EXISTS idx_site_analytics_daily_wd
    ON public.site_analytics_daily (website_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_site_analytics_pages_wd
    ON public.site_analytics_pages_daily (website_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_site_analytics_referrers_wd
    ON public.site_analytics_referrers_daily (website_id, date DESC);
-- Purge scans by date only
CREATE INDEX IF NOT EXISTS idx_site_analytics_visitors_date
    ON public.site_analytics_visitors_daily (date);

-- =============================================================================
-- SECTION B — RLS: enabled with NO anon/authenticated policies.
--   The browser never reads these tables; all reads go through the FastAPI
--   backend (service role, bypasses RLS). Consistent with migration 049's
--   direction: zero anon-key surface.
-- =============================================================================

ALTER TABLE public.site_analytics_daily            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_analytics_pages_daily      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_analytics_referrers_daily  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_analytics_visitors_daily   ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.site_analytics_daily           FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.site_analytics_pages_daily     FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.site_analytics_referrers_daily FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.site_analytics_visitors_daily  FROM PUBLIC, anon, authenticated;

-- The FastAPI backend connects as service_role (bypasses RLS). Grant it
-- table privileges explicitly — matching the repo convention (migration
-- 002 GRANTs every delivery table TO service_role) rather than relying on
-- Supabase default privileges.
GRANT ALL ON public.site_analytics_daily           TO service_role;
GRANT ALL ON public.site_analytics_pages_daily     TO service_role;
GRANT ALL ON public.site_analytics_referrers_daily TO service_role;
GRANT ALL ON public.site_analytics_visitors_daily  TO service_role;

-- =============================================================================
-- SECTION C — atomic write-time rollup RPC
--   One round trip per pageview; the uniques logic (dedup insert + conditional
--   counter bump) must be atomic, which four separate PostgREST calls cannot
--   guarantee. SECURITY DEFINER so only the function needs execute rights;
--   direct table grants stay revoked. Execution is service-role only.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.track_site_pageview(
    p_website_id UUID,
    p_date DATE,
    p_visitor_hash TEXT,
    p_device TEXT,
    p_page_path TEXT,
    p_referrer_source TEXT
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_new_unique INT := 0;
BEGIN
    INSERT INTO site_analytics_visitors_daily (website_id, date, visitor_hash)
    VALUES (p_website_id, p_date, p_visitor_hash)
    ON CONFLICT DO NOTHING;
    IF FOUND THEN
        v_new_unique := 1;
    END IF;

    INSERT INTO site_analytics_daily AS d
        (website_id, date, total_views, unique_visitors,
         mobile_views, tablet_views, desktop_views)
    VALUES
        (p_website_id, p_date, 1, v_new_unique,
         (p_device = 'mobile')::int,
         (p_device = 'tablet')::int,
         (p_device = 'desktop')::int)
    ON CONFLICT (website_id, date) DO UPDATE SET
        total_views     = d.total_views + 1,
        unique_visitors = d.unique_visitors + v_new_unique,
        mobile_views    = d.mobile_views  + (p_device = 'mobile')::int,
        tablet_views    = d.tablet_views  + (p_device = 'tablet')::int,
        desktop_views   = d.desktop_views + (p_device = 'desktop')::int,
        updated_at      = now();

    INSERT INTO site_analytics_pages_daily (website_id, date, page_path, views)
    VALUES (p_website_id, p_date, COALESCE(NULLIF(p_page_path, ''), '/'), 1)
    ON CONFLICT (website_id, date, page_path) DO UPDATE
        SET views = site_analytics_pages_daily.views + 1;

    INSERT INTO site_analytics_referrers_daily (website_id, date, referrer_source, views)
    VALUES (p_website_id, p_date, COALESCE(NULLIF(p_referrer_source, ''), 'direct'), 1)
    ON CONFLICT (website_id, date, referrer_source) DO UPDATE
        SET views = site_analytics_referrers_daily.views + 1;
END
$$;

-- Functions grant EXECUTE to PUBLIC on creation; revoke that, then grant
-- back to service_role ONLY. Without the explicit grant the backend's RPC
-- call (as service_role) would fail with "permission denied for function".
REVOKE ALL ON FUNCTION public.track_site_pageview(UUID, DATE, TEXT, TEXT, TEXT, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.track_site_pageview(UUID, DATE, TEXT, TEXT, TEXT, TEXT)
    TO service_role;

-- =============================================================================
-- SECTION D — dedup-row retention purge (called daily by the backend
--             AnalyticsCleanupScheduler; 2-day default keeps yesterday's rows
--             through any timezone edge while today's counting continues)
-- =============================================================================

CREATE OR REPLACE FUNCTION public.cleanup_analytics_visitor_hashes(
    p_retention_days INT DEFAULT 2
) RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_deleted INT;
BEGIN
    DELETE FROM site_analytics_visitors_daily
    WHERE date < CURRENT_DATE - p_retention_days;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END
$$;

REVOKE ALL ON FUNCTION public.cleanup_analytics_visitor_hashes(INT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.cleanup_analytics_visitor_hashes(INT)
    TO service_role;

-- =============================================================================
-- SECTION E — legacy table: PDPA purge of stored raw IPs.
--   The backend stops writing to public.analytics / analytics_daily in the
--   same release; the table is kept read-only for history. Dropping the
--   column (not just null-ing it) removes the data and the temptation alike.
--   Wrapped so a prod schema without the table/column is a harmless no-op.
-- =============================================================================

DO $$
BEGIN
    ALTER TABLE public.analytics DROP COLUMN IF EXISTS ip_address;
EXCEPTION WHEN undefined_table THEN
    RAISE NOTICE 'legacy analytics table absent; ip purge skipped';
END
$$;

-- =============================================================================
-- SECTION F — best-effort backfill of legacy daily rollups so merchants keep
--   their history on day one. Legacy analytics_daily.project_id is a hostname
--   string ('mybistro.binaapp.my' or bare subdomain); join on the first label.
--   Wrapped: the live table has known schema drift, so any mismatch degrades
--   to a NOTICE instead of failing the migration.
-- =============================================================================

DO $$
BEGIN
    INSERT INTO public.site_analytics_daily
        (website_id, date, total_views, unique_visitors, mobile_views, desktop_views)
    SELECT w.id,
           a.date,
           COALESCE(a.total_views, 0),
           COALESCE(a.unique_visitors, 0),
           COALESCE(a.mobile_views, 0),
           COALESCE(a.desktop_views, 0)
    FROM public.analytics_daily a
    JOIN public.websites w
      ON w.subdomain = split_part(a.project_id::text, '.', 1)
    ON CONFLICT (website_id, date) DO NOTHING;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'analytics_daily backfill skipped: %', SQLERRM;
END
$$;

COMMIT;

-- =============================================================================
-- POST-APPLY VERIFICATION (run manually)
-- =============================================================================
-- 1) Tables exist and are RLS-locked (rowsecurity = true, zero policies):
-- SELECT c.relname, c.relrowsecurity,
--        (SELECT count(*) FROM pg_policies p WHERE p.tablename = c.relname) AS policies
-- FROM pg_class c
-- WHERE c.relname LIKE 'site_analytics_%';
--
-- 2) Legacy IPs are gone:
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'analytics' AND column_name = 'ip_address';  -- expect 0 rows
--
-- 3) RPC smoke test (as service role):
-- SELECT public.track_site_pageview(
--   (SELECT id FROM public.websites LIMIT 1), CURRENT_DATE,
--   'testhash0000000000000000000000ab', 'mobile', '/', 'direct');
-- SELECT * FROM public.site_analytics_daily ORDER BY updated_at DESC LIMIT 1;

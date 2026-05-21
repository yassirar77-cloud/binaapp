-- Migration 038: Per-website analytics opt-out flag
--
-- Adds a boolean column to public.websites that controls whether the
-- BinaApp first-party visitor analytics tracker is active for that
-- website. When false:
--   * The publish pipeline strips the <!-- BinaApp Analytics --> <script>
--     block from the website's HTML before saving it to the websites row
--     (see backend/app/main.py — strip-at-publish boundary).
--   * The /api/analytics/track endpoint rejects (HTTP 204) any event
--     whose project_id (hostname) resolves to this website.
--
-- Default true preserves current behaviour for all existing websites.
-- New websites inherit the default and can be opted out from the
-- per-website settings UI.
--
-- Manual run instruction (per Step 3a Task 5b protocol — this file is
-- committed but NOT auto-applied; run in the Supabase SQL editor):
--
--   1. Open Supabase project → SQL editor
--   2. Paste the ALTER statement below
--   3. Run; expect "ALTER TABLE" success
--   4. Verify with:
--        SELECT column_name, data_type, column_default, is_nullable
--        FROM information_schema.columns
--        WHERE table_schema='public' AND table_name='websites'
--          AND column_name='analytics_enabled';

ALTER TABLE public.websites
    ADD COLUMN IF NOT EXISTS analytics_enabled BOOLEAN DEFAULT true NOT NULL;

COMMENT ON COLUMN public.websites.analytics_enabled IS
    'When false, BinaApp first-party visitor tracking script is stripped from generated HTML and /api/analytics/track endpoint rejects requests for this website. Default true for backwards compatibility.';

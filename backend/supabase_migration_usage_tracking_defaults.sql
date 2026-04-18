-- ============================================================================
-- usage_tracking — restore DEFAULT 0 on every counter column (Bug 4 fix)
-- ============================================================================
--
-- Production DB drifted from migration 005_subscription_management.sql: the
-- addon_* columns were created as NOT NULL but lost their DEFAULT 0, so upserts
-- that omit them fail with Postgres 23502 (not_null_violation). Example prod
-- error row: `(..., 0, 0, null, null, 2026-04-18...)` — the two NULLs were
-- addon_websites_used and addon_ai_hero_used.
--
-- This migration is idempotent (re-runnable) and uses `SET DEFAULT` which is
-- metadata-only — no table rewrite, no lock upgrade beyond AccessShareLock.
-- Any existing NULL rows are filled with 0 in a one-time backfill below.

-- 1. Restore DEFAULT 0 on every counter column so future omissions are safe.
ALTER TABLE public.usage_tracking
    ALTER COLUMN websites_count        SET DEFAULT 0,
    ALTER COLUMN menu_items_count      SET DEFAULT 0,
    ALTER COLUMN ai_hero_used          SET DEFAULT 0,
    ALTER COLUMN ai_images_used        SET DEFAULT 0,
    ALTER COLUMN delivery_zones_count  SET DEFAULT 0,
    ALTER COLUMN riders_count          SET DEFAULT 0,
    ALTER COLUMN addon_websites_used   SET DEFAULT 0,
    ALTER COLUMN addon_ai_hero_used    SET DEFAULT 0,
    ALTER COLUMN addon_ai_images_used  SET DEFAULT 0,
    ALTER COLUMN addon_riders_used     SET DEFAULT 0,
    ALTER COLUMN addon_zones_used      SET DEFAULT 0;

-- 2. Ensure timestamp columns have sane defaults too (they may have drifted).
ALTER TABLE public.usage_tracking
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

-- 3. Backfill any existing rows that slipped in with NULL counters before the
--    DEFAULTs were restored.  COALESCE keeps non-null values untouched.
UPDATE public.usage_tracking SET
    websites_count        = COALESCE(websites_count,        0),
    menu_items_count      = COALESCE(menu_items_count,      0),
    ai_hero_used          = COALESCE(ai_hero_used,          0),
    ai_images_used        = COALESCE(ai_images_used,        0),
    delivery_zones_count  = COALESCE(delivery_zones_count,  0),
    riders_count          = COALESCE(riders_count,          0),
    addon_websites_used   = COALESCE(addon_websites_used,   0),
    addon_ai_hero_used    = COALESCE(addon_ai_hero_used,    0),
    addon_ai_images_used  = COALESCE(addon_ai_images_used,  0),
    addon_riders_used     = COALESCE(addon_riders_used,     0),
    addon_zones_used      = COALESCE(addon_zones_used,      0)
WHERE
       websites_count        IS NULL
    OR menu_items_count      IS NULL
    OR ai_hero_used          IS NULL
    OR ai_images_used        IS NULL
    OR delivery_zones_count  IS NULL
    OR riders_count          IS NULL
    OR addon_websites_used   IS NULL
    OR addon_ai_hero_used    IS NULL
    OR addon_ai_images_used  IS NULL
    OR addon_riders_used     IS NULL
    OR addon_zones_used      IS NULL;

-- 4. Verify: after running this, every counter column should have a default.
-- Run this query to confirm:
--   SELECT column_name, column_default, is_nullable
--   FROM information_schema.columns
--   WHERE table_name = 'usage_tracking'
--   ORDER BY ordinal_position;

-- ==========================================================================
-- Migration 036: Drop UNIQUE(user_id) on subscriptions
-- ==========================================================================
-- Reason: production code already supports multiple subscription rows per
-- user (commit 13622db picker logic; websites.py:97 ORDER BY ...). Phase 2
-- requires:
--   - Migration 033 INSERT for yassirar77 (currently no row — fine alone)
--   - Migration 037 INSERT new active Free row for 4 Khulafa users who
--     already have an expired row each (THIS is the conflict driver)
--   - Migration 035 trigger inserting subscription on auth.users INSERT
--
-- Confirmed name on production: subscriptions_user_id_key (constraint + index).
-- Keep idempotent IF EXISTS forms in case prod state drifts between now
-- and apply time.
--
-- Replaces UNIQUE index with a non-unique one so user_id lookups stay fast,
-- plus a composite covering the "newest active row per user" pattern used
-- in websites.py:89-100, quota.ts:101-109, and subscription_service.py:147.
-- ==========================================================================

BEGIN;

-- Drop the UNIQUE constraint (this also drops the backing index).
ALTER TABLE public.subscriptions
  DROP CONSTRAINT IF EXISTS subscriptions_user_id_key;

-- Belt-and-braces in case any naming variant exists.
ALTER TABLE public.subscriptions
  DROP CONSTRAINT IF EXISTS subscriptions_user_id_unique;
DROP INDEX IF EXISTS public.subscriptions_user_id_key;
DROP INDEX IF EXISTS public.subscriptions_user_id_unique;

-- Non-unique replacement so per-user reads stay fast.
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id
  ON public.subscriptions(user_id);

-- Composite for newest-active-per-user. Matches the ORDER BY pattern in
-- subscription_service.get_user_subscription, websites.py inline gate,
-- quota.ts getWebsiteLimit, and website_lock_checker.
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status_period
  ON public.subscriptions(
       user_id,
       status,
       current_period_end DESC NULLS LAST,
       end_date           DESC NULLS LAST
     );

DO $$
DECLARE
  v_remaining INT;
BEGIN
  SELECT COUNT(*) INTO v_remaining
  FROM pg_constraint
  WHERE conrelid = 'public.subscriptions'::regclass
    AND contype  = 'u'
    AND conkey = (
      SELECT ARRAY[attnum]::smallint[]
      FROM pg_attribute
      WHERE attrelid = 'public.subscriptions'::regclass
        AND attname  = 'user_id'
    );
  RAISE NOTICE 'Migration 036 complete. UNIQUE constraints on user_id remaining: % (expected 0)', v_remaining;
END $$;

COMMIT;

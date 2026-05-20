-- ==========================================================================
-- Migration 033: Seed missing free subscription for yassirar77@gmail.com
-- ==========================================================================
-- Targets user_id = 7feab79a-6937-4c59-a883-3a2f7609b734 (yassirar77@gmail.com)
-- Inserts: tier='free', plan_id=8814f50f-... (Free plan), status='active'.
--
-- Idempotent: NOT EXISTS guard skips if any subscription row exists for this
-- user. Re-runs are no-ops.
--
-- Safe to run now: UNIQUE(user_id) was dropped in migration 036. (Migrations
-- 033 must run AFTER 036 for the bare INSERT to be safe; in this phase 036
-- runs before 033 — see the apply order in commits.)
-- ==========================================================================

BEGIN;

INSERT INTO public.subscriptions
    (user_id, tier, status, plan_id, start_date, created_at, updated_at)
SELECT
    u.id,
    'free',
    'active',
    (SELECT plan_id FROM public.subscription_plans WHERE plan_name = 'free'),
    NOW(),
    NOW(),
    NOW()
FROM auth.users u
WHERE u.email = 'yassirar77@gmail.com'
  AND NOT EXISTS (
    SELECT 1 FROM public.subscriptions s WHERE s.user_id = u.id
  );

DO $$
DECLARE
  v_rows INT;
BEGIN
  SELECT COUNT(*) INTO v_rows
  FROM public.subscriptions s
  JOIN auth.users u ON u.id = s.user_id
  WHERE u.email = 'yassirar77@gmail.com';
  RAISE NOTICE 'Migration 033 complete. yassirar77 now has % subscription row(s) (expected 1)', v_rows;
END $$;

COMMIT;

-- ==========================================================================
-- Migration 037: Backfill active Free subscription for users with no
--                active subscription row
-- ==========================================================================
-- Targets the 4 Khulafa accounts:
--   - khulafasign@gmail.com         (existing: starter/expired Jan 2026)
--   - khulafavista@gmail.com        (existing: pro/expired     Jan 2026)
--   - khulafabistrofom@gmail.com    (existing: free/expired    Feb 2026)
--   - restorankhulafa77@gmail.com   (existing: starter/expired Mar 2026)
--
-- For each: inserts a NEW row with tier='free', plan_id=<free uuid>,
-- status='active', start_date=NOW(). Their old expired rows remain
-- untouched as audit history.
--
-- Safe to run: Migration 036 dropped UNIQUE(user_id), so multi-row
-- per user is allowed. NOT EXISTS guard means re-runs are no-ops.
-- ==========================================================================

BEGIN;

INSERT INTO public.subscriptions
    (user_id, tier, status, plan_id, start_date, created_at, updated_at)
SELECT DISTINCT
    s.user_id,
    'free',
    'active',
    (SELECT plan_id FROM public.subscription_plans WHERE plan_name = 'free'),
    NOW(),
    NOW(),
    NOW()
FROM public.subscriptions s
WHERE NOT EXISTS (
    SELECT 1 FROM public.subscriptions s2
    WHERE s2.user_id = s.user_id AND s2.status = 'active'
);

DO $$
DECLARE
  v_orphans INT;
BEGIN
  SELECT COUNT(*) INTO v_orphans
  FROM (
    SELECT user_id
    FROM public.subscriptions
    GROUP BY user_id
    HAVING SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) = 0
  ) x;
  RAISE NOTICE 'Migration 037 complete. Users still without active subscription: % (expected 0)', v_orphans;
END $$;

COMMIT;

-- ==========================================================================
-- Migration 032: Backfill subscriptions.plan_id from tier
-- ==========================================================================
-- Resolves plan_id by joining subscriptions.tier → subscription_plans.plan_name.
-- For our 4 NULL rows this resolves to:
--   khulafasign (starter)        → a253ccab-ef8c-4db5-a07e-cd88b74daea3
--   khulafavista (pro)           → b646d4b0-6f54-4904-b412-392050838309
--   restorankhulafa77 (starter)  → a253ccab-ef8c-4db5-a07e-cd88b74daea3
--   cheryltan227 (free)          → 8814f50f-f2cd-4000-b5e0-e8906442386b
--
-- Safe: UPDATE only. WHERE plan_id IS NULL guarantees we never overwrite
-- correctly-set rows. Idempotent — re-running is a no-op once filled.
-- ==========================================================================

BEGIN;

WITH resolved AS (
  SELECT s.id AS sub_id, sp.plan_id
  FROM public.subscriptions s
  JOIN public.subscription_plans sp ON sp.plan_name = s.tier
  WHERE s.plan_id IS NULL
)
UPDATE public.subscriptions s
SET plan_id    = r.plan_id,
    updated_at = NOW()
FROM resolved r
WHERE s.id = r.sub_id;

DO $$
DECLARE
  v_remaining INT;
BEGIN
  SELECT COUNT(*) INTO v_remaining
  FROM public.subscriptions
  WHERE plan_id IS NULL;
  RAISE NOTICE 'Migration 032 complete. Rows still with NULL plan_id: % (expected 0)', v_remaining;
END $$;

COMMIT;

-- ==========================================================================
-- Migration 042: Resync subscriptions.plan_id to match tier
-- ==========================================================================
-- Stronger successor to migration 032. That one only fixed plan_id IS NULL
-- rows, but the real production failure mode is plan_id NON-NULL but WRONG:
-- a free user signs up (plan_id -> free plan), later pays to upgrade, and the
-- old payment code set tier='starter' WITHOUT touching plan_id — so the row
-- ends up tier='starter' yet plan_id still points at the FREE plan, whose
-- features carry can_publish_subdomain:false. The publish gate joins via
-- plan_id, lands on free, and serves the upgrade paywall to a paying user.
--
-- This resyncs plan_id to the plan whose plan_name == tier for EVERY row where
-- they disagree (NULL or wrong). IS DISTINCT FROM handles NULLs correctly.
--
-- Idempotent: re-running is a no-op once every row's plan_id matches its tier.
-- Rows whose tier has no matching plan are left untouched.
--
-- The application fix (payments.py writes plan_id on every payment, including
-- the PATCH/upgrade path) prevents NEW drift; this heals existing rows.
-- ==========================================================================

BEGIN;

UPDATE public.subscriptions AS s
SET plan_id    = p.plan_id,
    updated_at = NOW()
FROM public.subscription_plans AS p
WHERE s.tier = p.plan_name
  AND s.plan_id IS DISTINCT FROM p.plan_id;

DO $$
DECLARE
  v_mismatched INT;
BEGIN
  SELECT COUNT(*) INTO v_mismatched
  FROM public.subscriptions s
  JOIN public.subscription_plans p ON p.plan_name = s.tier
  WHERE s.plan_id IS DISTINCT FROM p.plan_id;
  RAISE NOTICE 'Migration 042 complete. Rows whose plan_id still disagrees with tier: % (expected 0)', v_mismatched;
END $$;

COMMIT;

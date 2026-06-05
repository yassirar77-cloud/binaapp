-- ==========================================================================
-- Migration 043: Structurally enforce subscriptions.plan_id == tier's plan
-- ==========================================================================
-- WHY: plan_id drift (tier says starter/basic/pro but plan_id still points at
-- the signup-default FREE plan) has now surfaced three times, each via a
-- different write path (legacy /subscribe/{tier} callback, legacy late-verify,
-- modern verify-payment apply helpers). The serve-time subdomain gate joins
-- subscriptions.plan_id -> subscription_plans to read can_publish_subdomain,
-- so any drifted row serves the upgrade paywall to a paying customer.
--
-- The code paths have all been patched to resolve plan_id from tier, but a
-- code fix only holds at the sites we remembered to touch. This migration
-- makes the invariant impossible to violate at the DB level: a BEFORE trigger
-- forces plan_id to the plan that matches `tier` on every write that touches
-- `tier` or `plan_id`. After this, tier and plan_id can never disagree no
-- matter which path (or future path) writes the row.
--
-- DESIGN:
--   * BEFORE INSERT OR UPDATE OF tier, plan_id — fires on exactly the writes
--     that could introduce drift, and skips unrelated updates (end_date,
--     lock fields, etc.) so it costs nothing on the hot lock/renew paths.
--   * Resolves plan_id from `tier` via subscription_plans.plan_name. `tier`
--     is the source of truth in this codebase; plan_id mirrors it.
--   * FAIL-SAFE: if `tier` does not resolve to a known plan (unexpected tier
--     value), plan_id is left untouched rather than nulled — never makes a
--     row worse than it already was.
--   * SECURITY DEFINER + SET row_security = off so the plan lookup is not
--     filtered by RLS regardless of the writing role (mirrors migration 035).
--
-- Also reconciles existing rows once so current drift is healed in the same
-- reviewable unit (idempotent: only rewrites rows that actually disagree).
--
-- IDEMPOTENT: CREATE OR REPLACE FUNCTION + DROP TRIGGER IF EXISTS +
-- CREATE TRIGGER. Re-running is a no-op.
-- ==========================================================================

BEGIN;

-- ---------- STEP 1: The sync function ----------
CREATE OR REPLACE FUNCTION public.sync_subscription_plan_id()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET row_security = off
AS $$
DECLARE
    v_plan_id UUID;
BEGIN
    IF NEW.tier IS NOT NULL THEN
        SELECT plan_id INTO v_plan_id
        FROM public.subscription_plans
        WHERE plan_name = NEW.tier
        LIMIT 1;

        -- Only override when the tier resolves to a known plan. An unknown
        -- tier leaves plan_id untouched (fail-safe) instead of nulling it.
        IF v_plan_id IS NOT NULL THEN
            NEW.plan_id := v_plan_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- ---------- STEP 2: Attach the trigger ----------
-- UPDATE OF tier, plan_id: fire only when one of these columns is in the SET
-- list. Every way drift can be introduced (insert with wrong plan_id, change
-- tier without plan_id, change plan_id away from tier) touches one of them and
-- is therefore corrected; unrelated updates never pay for the lookup.
DROP TRIGGER IF EXISTS trg_sync_subscription_plan_id ON public.subscriptions;
CREATE TRIGGER trg_sync_subscription_plan_id
    BEFORE INSERT OR UPDATE OF tier, plan_id ON public.subscriptions
    FOR EACH ROW EXECUTE FUNCTION public.sync_subscription_plan_id();

-- ---------- STEP 3: One-time reconcile of existing rows ----------
-- Heal any row whose plan_id currently disagrees with its tier. WHERE clause
-- guarantees we only rewrite genuine mismatches (and never overwrite a row
-- whose tier doesn't resolve to a known plan).
UPDATE public.subscriptions s
SET plan_id    = sp.plan_id,
    updated_at = NOW()
FROM public.subscription_plans sp
WHERE sp.plan_name = s.tier
  AND s.tier IS NOT NULL
  AND (s.plan_id IS NULL OR s.plan_id <> sp.plan_id);

-- ---------- STEP 4: Verify ----------
DO $$
DECLARE
    v_trigger_exists BOOLEAN;
    v_remaining_mismatch INT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_sync_subscription_plan_id'
          AND tgrelid = 'public.subscriptions'::regclass
    ) INTO v_trigger_exists;

    SELECT COUNT(*) INTO v_remaining_mismatch
    FROM public.subscriptions s
    JOIN public.subscription_plans sp ON sp.plan_name = s.tier
    WHERE s.tier IS NOT NULL
      AND (s.plan_id IS NULL OR s.plan_id <> sp.plan_id);

    RAISE NOTICE 'Migration 043 complete. trigger exists: %, resolvable rows still mismatched: % (expected 0)',
        v_trigger_exists, v_remaining_mismatch;
END $$;

COMMIT;

-- ==========================================================================
-- DOWN MIGRATION (manual, copy-paste to revert)
-- ==========================================================================
-- BEGIN;
-- DROP TRIGGER IF EXISTS trg_sync_subscription_plan_id ON public.subscriptions;
-- DROP FUNCTION IF EXISTS public.sync_subscription_plan_id();
-- -- Note: the STEP 3 reconcile is NOT reverted — restoring drift would only
-- --       re-break the subdomain gate, so the healed rows are left correct.
-- COMMIT;

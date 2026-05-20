-- ==========================================================================
-- Migration 035: Trigger creates subscription row alongside profile
-- ==========================================================================
-- Replaces the trigger from migration 018 (which only created a profiles
-- row). The new version inserts BOTH a profiles row AND an active 'free'
-- subscription with plan_id resolved at trigger time.
--
-- Migration 008 declared UNIQUE(user_id) on public.subscriptions; that
-- constraint was dropped in Phase 2 (migration 036). So we use a BARE
-- INSERT here — no ON CONFLICT clause. If /auth/register ever re-introduces
-- its own subscription INSERT (it doesn't, after the Phase-2 auth.py
-- change), a duplicate row would be accepted; readers already pick
-- newest-active-row.
--
-- RLS note: SECURITY DEFINER alone is NOT enough to bypass RLS on
-- public.subscriptions in this database — the service-role-defined function
-- still tripped the row-level policies during the trigger fire path,
-- because Supabase's defaults can leave row_security ON even for
-- SECURITY DEFINER functions. The `SET row_security = off` function
-- option disables RLS for statements executed inside this function only.
-- Equivalent to running the function with BYPASSRLS, scoped to this fn.
--
-- Idempotent migration: CREATE OR REPLACE FUNCTION + DROP TRIGGER IF
-- EXISTS + CREATE TRIGGER.
-- ==========================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET row_security = off
AS $$
DECLARE
    v_free_plan_id UUID;
BEGIN
    -- Profile row (carried over from migration 018, unchanged behavior).
    INSERT INTO public.profiles (id, full_name, created_at, updated_at)
    VALUES (
        NEW.id,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            split_part(NEW.email, '@', 1)
        ),
        NOW(),
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;

    -- Resolve the 'free' plan_id at trigger time so the row joins
    -- correctly to subscription_plans. If the 'free' row is missing
    -- (shouldn't happen post-migration 025), we still insert with NULL
    -- plan_id — migration 032's backfill catches stragglers, and
    -- limit gating tolerates NULL via the plan_features.py guard.
    SELECT plan_id INTO v_free_plan_id
    FROM public.subscription_plans
    WHERE plan_name = 'free'
    LIMIT 1;

    -- Bare INSERT — UNIQUE(user_id) was dropped in migration 036.
    INSERT INTO public.subscriptions
        (user_id, tier, status, plan_id, start_date, created_at, updated_at)
    VALUES
        (NEW.id, 'free', 'active', v_free_plan_id, NOW(), NOW(), NOW());

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

DO $$
DECLARE
    v_trigger_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'on_auth_user_created'
          AND tgrelid = 'auth.users'::regclass
    ) INTO v_trigger_exists;
    RAISE NOTICE 'Migration 035 complete. on_auth_user_created exists: %', v_trigger_exists;
END $$;

COMMIT;

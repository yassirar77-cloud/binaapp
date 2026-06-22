-- ==========================================================================
-- BINAAPP PROMO CODE REDEMPTION SYSTEM
-- Migration: 047_promo_code_redemption.sql
-- Created: 2026-06-22
-- ==========================================================================
-- PURPOSE:
-- Launch promo — the first N users (default 20) to redeem a promo code get the
-- RM5 Starter tier FREE for 1 month (no payment taken). After expiry the daily
-- subscription cron downgrades/locks them exactly like any unpaid user, because
-- the comp sub is written with status='active' + end_date = now + 1 month — the
-- SAME fields the cron (app/cron/subscription_cron.py) keys off.
--
-- DISTINGUISHING A COMP SUB FROM A PAID ONE:
--   subscriptions.is_promo = TRUE, price = 0, toyyibpay_bill_code = NULL.
--
-- ATOMICITY (no race on the 20th slot):
--   redeem_promo_code() takes a transaction-scoped advisory lock keyed on the
--   promo code BEFORE it counts existing redemptions, so two concurrent
--   redemptions of the last slot are serialised — the second sees the updated
--   count and is rejected with 'promo_full'. The UNIQUE(user_id) constraint on
--   promo_redemptions is a second backstop against double-redeem.
--
-- CONFIGURABILITY (no redeploy):
--   The code string, the cap and the duration live in the promo_config row.
--   Change them at any time with plain SQL, e.g.
--     UPDATE public.promo_config SET code = 'NEWCODE', max_redemptions = 50;
-- ==========================================================================

-- ==========================================================================
-- SECTION 1: MARK PROMO/COMP SUBSCRIPTIONS
-- ==========================================================================
-- Add a flag so a comp (promo) subscription is distinguishable from a real
-- paid one. The cron does not need this column (it keys off status/end_date),
-- but reporting, support and the paid-activation flow do.

ALTER TABLE public.subscriptions
    ADD COLUMN IF NOT EXISTS is_promo BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.subscriptions.is_promo IS
    'TRUE when this subscription was granted free via a promo code (comp sub), '
    'not paid through ToyyibPay. price=0 and toyyibpay_bill_code IS NULL for these.';

-- ==========================================================================
-- SECTION 2: PROMO CONFIG (single live-editable config row)
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.promo_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    code TEXT NOT NULL,
    max_redemptions INTEGER NOT NULL DEFAULT 20,
    duration_days INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Enforce a single config row.
    CONSTRAINT promo_config_singleton CHECK (id = 1)
);

COMMENT ON TABLE public.promo_config IS
    'Single-row promo configuration. Edit with SQL to change the code/cap/'
    'duration without a redeploy, e.g. UPDATE promo_config SET max_redemptions=50.';

-- Seed the launch promo. ON CONFLICT DO NOTHING so re-running the migration
-- never clobbers an admin-edited config row.
INSERT INTO public.promo_config (id, code, max_redemptions, duration_days, is_active)
VALUES (1, 'BINA20', 20, 30, TRUE)
ON CONFLICT (id) DO NOTHING;

-- ==========================================================================
-- SECTION 3: PROMO REDEMPTIONS
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.promo_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- One redemption per user, ever. This UNIQUE constraint is the hard
    -- backstop against double-redeem (even across different codes).
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    subscription_id UUID REFERENCES public.subscriptions(id) ON DELETE SET NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'expired', 'cancelled'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT promo_redemptions_status_check
        CHECK (status IN ('active', 'expired', 'cancelled'))
);

-- Used by the slot-count query inside redeem_promo_code (case-insensitive on code).
CREATE INDEX IF NOT EXISTS idx_promo_redemptions_code
    ON public.promo_redemptions (lower(code));

CREATE INDEX IF NOT EXISTS idx_promo_redemptions_expires_at
    ON public.promo_redemptions (expires_at);

ALTER TABLE public.promo_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.promo_redemptions ENABLE ROW LEVEL SECURITY;

-- Users can see their own redemption; everything else is service-role only.
DROP POLICY IF EXISTS "Users can view own promo redemption" ON public.promo_redemptions;
CREATE POLICY "Users can view own promo redemption"
    ON public.promo_redemptions FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role manages promo redemptions" ON public.promo_redemptions;
CREATE POLICY "Service role manages promo redemptions"
    ON public.promo_redemptions FOR ALL
    USING (true);

DROP POLICY IF EXISTS "Service role manages promo config" ON public.promo_config;
CREATE POLICY "Service role manages promo config"
    ON public.promo_config FOR ALL
    USING (true);

-- ==========================================================================
-- SECTION 4: ATOMIC REDEMPTION FUNCTION
-- ==========================================================================
-- Returns JSONB. On success: {success:true, status:'redeemed', expires_at, ...}.
-- On failure: {success:false, status:'<reason>'} where reason is one of
-- inactive | invalid_code | already_redeemed | has_active_plan | promo_full.

CREATE OR REPLACE FUNCTION public.redeem_promo_code(
    p_user_id UUID,
    p_code TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_config        public.promo_config%ROWTYPE;
    v_norm_input    TEXT;
    v_norm_code     TEXT;
    v_used          INTEGER;
    v_expires_at    TIMESTAMPTZ;
    v_now           TIMESTAMPTZ := NOW();
    v_plan_id       UUID;
    v_sub_id        UUID;
BEGIN
    -- 1. Load config.
    SELECT * INTO v_config FROM public.promo_config WHERE id = 1;
    IF NOT FOUND OR NOT v_config.is_active THEN
        RETURN jsonb_build_object('success', false, 'status', 'inactive');
    END IF;

    v_norm_input := lower(btrim(COALESCE(p_code, '')));
    v_norm_code  := lower(btrim(v_config.code));

    -- 2. Serialise all redemptions of this code BEFORE counting, so the cap is
    --    enforced atomically (no two callers can both grab the final slot).
    PERFORM pg_advisory_xact_lock(hashtext('binaapp_promo:' || v_norm_code));

    -- 3. Validate the submitted code (case-insensitive, trimmed).
    IF v_norm_input = '' OR v_norm_input <> v_norm_code THEN
        RETURN jsonb_build_object('success', false, 'status', 'invalid_code');
    END IF;

    -- 4. One redemption per user, ever.
    IF EXISTS (SELECT 1 FROM public.promo_redemptions WHERE user_id = p_user_id) THEN
        RETURN jsonb_build_object('success', false, 'status', 'already_redeemed');
    END IF;

    -- 5. Block users who already have an active PAID subscription. A free /
    --    legacy / expired / locked user is allowed to claim the free month.
    IF EXISTS (
        SELECT 1 FROM public.subscriptions
        WHERE user_id = p_user_id
          AND status = 'active'
          AND COALESCE(is_promo, false) = false
          AND tier IN ('starter', 'basic', 'pro')
          AND COALESCE(price, 0) > 0
    ) THEN
        RETURN jsonb_build_object('success', false, 'status', 'has_active_plan');
    END IF;

    -- 6. Enforce the slot cap (count is now race-free under the advisory lock).
    SELECT count(*) INTO v_used
    FROM public.promo_redemptions
    WHERE lower(code) = v_norm_code;

    IF v_used >= v_config.max_redemptions THEN
        RETURN jsonb_build_object(
            'success', false, 'status', 'promo_full',
            'max', v_config.max_redemptions, 'used', v_used
        );
    END IF;

    -- 7. Grant the comp Starter sub. expires_at uses the SAME field the cron
    --    reads (subscriptions.end_date), so expiry behaviour is identical to an
    --    unpaid sub.
    v_expires_at := v_now + (v_config.duration_days || ' days')::interval;
    SELECT plan_id INTO v_plan_id
    FROM public.subscription_plans WHERE plan_name = 'starter' LIMIT 1;

    -- Update the user's most-recent subscription row if one exists, else insert.
    -- (Mirrors payments.py::_process_subscription_payment which targets the
    -- latest row rather than assuming a single row per user — migration 036
    -- dropped the user_id UNIQUE constraint.)
    SELECT id INTO v_sub_id
    FROM public.subscriptions
    WHERE user_id = p_user_id
    ORDER BY current_period_end DESC NULLS LAST, end_date DESC NULLS LAST, created_at DESC
    LIMIT 1;

    IF v_sub_id IS NOT NULL THEN
        UPDATE public.subscriptions
        SET tier              = 'starter',
            status            = 'active',
            price             = 0,
            is_promo          = TRUE,
            plan_id           = COALESCE(v_plan_id, plan_id),
            start_date        = v_now,
            end_date          = v_expires_at,
            auto_renew        = FALSE,
            toyyibpay_bill_code = NULL,
            grace_period_end  = NULL,
            locked_at         = NULL,
            lock_reason       = NULL,
            updated_at        = v_now
        WHERE id = v_sub_id;
    ELSE
        INSERT INTO public.subscriptions
            (user_id, tier, status, price, is_promo, plan_id,
             start_date, end_date, auto_renew)
        VALUES
            (p_user_id, 'starter', 'active', 0, TRUE, v_plan_id,
             v_now, v_expires_at, FALSE)
        RETURNING id INTO v_sub_id;
    END IF;

    -- 8. Record the redemption (UNIQUE(user_id) makes a concurrent double-submit
    --    by the same user fail here even if it slipped past step 4).
    INSERT INTO public.promo_redemptions
        (user_id, code, subscription_id, granted_at, expires_at, status)
    VALUES
        (p_user_id, v_config.code, v_sub_id, v_now, v_expires_at, 'active');

    RETURN jsonb_build_object(
        'success', true,
        'status', 'redeemed',
        'tier', 'starter',
        'expires_at', v_expires_at,
        'subscription_id', v_sub_id,
        'slots_remaining', GREATEST(0, v_config.max_redemptions - (v_used + 1))
    );

EXCEPTION
    WHEN unique_violation THEN
        -- promo_redemptions.user_id UNIQUE tripped by a concurrent double-submit.
        RETURN jsonb_build_object('success', false, 'status', 'already_redeemed');
END;
$$;

-- ==========================================================================
-- SECTION 5: STATUS HELPER (for the frontend + admin)
-- ==========================================================================

CREATE OR REPLACE FUNCTION public.get_promo_status(p_user_id UUID DEFAULT NULL)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_config public.promo_config%ROWTYPE;
    v_used   INTEGER;
    v_already BOOLEAN := FALSE;
BEGIN
    SELECT * INTO v_config FROM public.promo_config WHERE id = 1;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('active', false, 'max', 0, 'used', 0, 'remaining', 0);
    END IF;

    SELECT count(*) INTO v_used
    FROM public.promo_redemptions
    WHERE lower(code) = lower(btrim(v_config.code));

    IF p_user_id IS NOT NULL THEN
        SELECT EXISTS (
            SELECT 1 FROM public.promo_redemptions WHERE user_id = p_user_id
        ) INTO v_already;
    END IF;

    RETURN jsonb_build_object(
        'active', v_config.is_active,
        'max', v_config.max_redemptions,
        'used', v_used,
        'remaining', GREATEST(0, v_config.max_redemptions - v_used),
        'already_redeemed', v_already
    );
END;
$$;

-- ==========================================================================
-- SECTION 6: ADMIN VIEW (who redeemed)
-- ==========================================================================
-- Joins redemptions to profiles for an at-a-glance "who redeemed" list.
-- profiles.id and promo_redemptions.user_id both reference auth.users(id).

CREATE OR REPLACE VIEW public.promo_redemptions_admin AS
SELECT
    pr.id,
    pr.user_id,
    pr.code,
    pr.subscription_id,
    pr.granted_at,
    pr.expires_at,
    pr.status,
    p.email,
    p.full_name,
    s.status AS subscription_status,
    s.end_date AS subscription_end_date
FROM public.promo_redemptions pr
LEFT JOIN public.profiles p ON p.id = pr.user_id
LEFT JOIN public.subscriptions s ON s.id = pr.subscription_id
ORDER BY pr.granted_at DESC;

-- ==========================================================================
-- SECTION 7: PERMISSIONS
-- ==========================================================================

GRANT SELECT ON public.promo_config TO authenticated, anon;
GRANT SELECT ON public.promo_redemptions TO authenticated;
GRANT ALL ON public.promo_config TO service_role;
GRANT ALL ON public.promo_redemptions TO service_role;
GRANT SELECT ON public.promo_redemptions_admin TO service_role;

-- redeem_promo_code is called by the backend with the service role key only.
GRANT EXECUTE ON FUNCTION public.redeem_promo_code(UUID, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_promo_status(UUID) TO service_role, authenticated;

-- ==========================================================================
-- SUCCESS MESSAGE
-- ==========================================================================

DO $$
BEGIN
    RAISE NOTICE '=== BinaApp Promo Code Redemption Migration Complete ===';
    RAISE NOTICE 'Tables: promo_config (1-row config), promo_redemptions';
    RAISE NOTICE 'Column: subscriptions.is_promo';
    RAISE NOTICE 'Functions: redeem_promo_code(user,code), get_promo_status(user)';
    RAISE NOTICE 'View: promo_redemptions_admin';
    RAISE NOTICE 'Seeded promo: code=BINA20, cap=20, duration=30 days';
    RAISE NOTICE 'Change config without redeploy via: UPDATE promo_config SET ...';
END $$;

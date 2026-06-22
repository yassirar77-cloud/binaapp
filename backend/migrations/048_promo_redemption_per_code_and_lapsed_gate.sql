-- ==========================================================================
-- BINAAPP PROMO CODE REDEMPTION — FOLLOW-UP FIXES
-- Migration: 048_promo_redemption_per_code_and_lapsed_gate.sql
-- Created: 2026-06-22
-- ==========================================================================
-- Two follow-ups to migration 047, applied before the promo launches:
--
-- FIX 2 — repeat promos across future campaigns:
--   047 put UNIQUE(user_id) on promo_redemptions, which permanently blocks a
--   user from EVER redeeming a future promo code. Swap it for UNIQUE(user_id,
--   code): at most one redemption PER code, but future campaigns stay open.
--   The table is empty (launch hasn't started) so this is a safe swap.
--
-- FIX 3 — close the lapse-then-redeem loophole:
--   047's gate only rejected status='active' paid subs, so a paid user whose
--   RM5 sub lapsed (status grace/locked/expired/cancelled) could grab a free
--   month. Tighten redeem_promo_code() to also reject a paid sub in any of
--   those lapsed states, with a distinct reason ('previously_subscribed').
--   Genuinely new users (free signup row: tier='free', price=0) are unaffected.
--
-- Idempotent: DROP ... IF EXISTS, a guarded ADD CONSTRAINT, and CREATE OR
-- REPLACE FUNCTION.
-- ==========================================================================

-- ==========================================================================
-- FIX 2: UNIQUE(user_id) -> UNIQUE(user_id, code)
-- ==========================================================================
-- The 047 column definition `user_id UUID NOT NULL UNIQUE` auto-named the
-- constraint promo_redemptions_user_id_key.
ALTER TABLE public.promo_redemptions
    DROP CONSTRAINT IF EXISTS promo_redemptions_user_id_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'promo_redemptions_user_code_key'
          AND conrelid = 'public.promo_redemptions'::regclass
    ) THEN
        ALTER TABLE public.promo_redemptions
            ADD CONSTRAINT promo_redemptions_user_code_key UNIQUE (user_id, code);
        RAISE NOTICE 'Added UNIQUE(user_id, code) on promo_redemptions';
    END IF;
END $$;

-- ==========================================================================
-- FIX 2 + FIX 3: updated redemption function
-- ==========================================================================
-- Changes vs 047:
--   * Step 4 "already redeemed" is now scoped to THIS code (per-campaign),
--     not "ever" — matching the new UNIQUE(user_id, code).
--   * Step 5 now has TWO reject branches: an active paid sub
--     (-> 'has_active_plan') and a lapsed paid sub in grace/locked/expired/
--     cancelled (-> 'previously_subscribed'). Both require a non-promo,
--     price>0 row so free/new users still qualify.
-- Everything else is identical to 047.

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
    v_sub_id        INTEGER;  -- matches public.subscriptions.id (integer in prod)
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

    -- 4. One redemption per user PER CODE (a user may still claim a future,
    --    different campaign code). UNIQUE(user_id, code) is the hard backstop.
    IF EXISTS (
        SELECT 1 FROM public.promo_redemptions
        WHERE user_id = p_user_id AND lower(code) = v_norm_code
    ) THEN
        RETURN jsonb_build_object('success', false, 'status', 'already_redeemed');
    END IF;

    -- 5a. Block users who already have an ACTIVE paid subscription.
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

    -- 5b. Block users whose PAID subscription has lapsed (grace/locked/expired/
    --     cancelled). Closes the lapse-then-redeem loophole: someone letting
    --     their RM5 lapse to grab a free month. The cron only changes status +
    --     lock fields on expiry, so a lapsed paid row still has price>0 and
    --     is_promo=false — making it cleanly distinguishable from a free user.
    IF EXISTS (
        SELECT 1 FROM public.subscriptions
        WHERE user_id = p_user_id
          AND status IN ('grace', 'locked', 'expired', 'cancelled')
          AND COALESCE(is_promo, false) = false
          AND tier IN ('starter', 'basic', 'pro')
          AND COALESCE(price, 0) > 0
    ) THEN
        RETURN jsonb_build_object('success', false, 'status', 'previously_subscribed');
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

    -- 8. Record the redemption (UNIQUE(user_id, code) makes a concurrent
    --    double-submit of the same code by the same user fail here).
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
        -- promo_redemptions UNIQUE(user_id, code) tripped by a concurrent
        -- double-submit of the same code.
        RETURN jsonb_build_object('success', false, 'status', 'already_redeemed');
END;
$$;

GRANT EXECUTE ON FUNCTION public.redeem_promo_code(UUID, TEXT) TO service_role;

DO $$
BEGIN
    RAISE NOTICE '=== Migration 048 complete ===';
    RAISE NOTICE 'promo_redemptions now UNIQUE(user_id, code) — repeat campaigns allowed';
    RAISE NOTICE 'redeem_promo_code now rejects lapsed paid subs (previously_subscribed)';
END $$;

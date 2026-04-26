-- ==========================================================================
-- BINAAPP MIGRATION 025: Add Free Tier Plan + Backfill
-- ==========================================================================
-- PROBLEM: subscription_plans has only starter/basic/pro. New users get
--          subscriptions.tier='free' (auto-created at signup) but no plan
--          row exists, so the FK join in get_user_limits() falls through
--          to starter, granting them subdomain publish rights.
--
-- FIX:
--   1. Insert 'free' plan row with can_publish_subdomain=false
--   2. Link existing tier='free' subscriptions to the new plan_id
--   3. Backfill usage_tracking rows for free users
--   4. Force published free-tier websites back to draft (idempotent)
--
-- IDEMPOTENT: Re-running this migration is a no-op for already-migrated rows.
-- REVERSIBLE: See down-migration block at bottom (commented out).
-- ==========================================================================

BEGIN;

-- ---------- STEP 1: Insert the 'free' plan ----------
INSERT INTO public.subscription_plans (
    plan_name, display_name, price,
    websites_limit, menu_items_limit, ai_hero_limit, ai_images_limit,
    delivery_zones_limit, riders_limit,
    features, is_active, sort_order
) VALUES (
    'free', 'Free', 0.00,
    1, 20, 3, 10,
    0, 0,
    '{"can_publish_subdomain": false, "can_use_custom_domain": false, "show_watermark": true, "preview_only": true}'::jsonb,
    true, 0
)
ON CONFLICT (plan_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    price = EXCLUDED.price,
    websites_limit = EXCLUDED.websites_limit,
    menu_items_limit = EXCLUDED.menu_items_limit,
    ai_hero_limit = EXCLUDED.ai_hero_limit,
    ai_images_limit = EXCLUDED.ai_images_limit,
    delivery_zones_limit = EXCLUDED.delivery_zones_limit,
    riders_limit = EXCLUDED.riders_limit,
    features = EXCLUDED.features,
    is_active = EXCLUDED.is_active,
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();

DO $$
DECLARE
    v_free_plan_id UUID;
    v_subs_linked  INT;
    v_usage_added  INT;
    v_sites_drafted INT;
    v_free_users   INT;
    v_free_drafts_existing INT;
BEGIN
    SELECT plan_id INTO v_free_plan_id
    FROM public.subscription_plans WHERE plan_name = 'free';

    RAISE NOTICE '----------------------------------------';
    RAISE NOTICE 'Migration 025: Free-tier backfill';
    RAISE NOTICE 'free plan_id = %', v_free_plan_id;

    -- ---------- STEP 2: Link existing free subscriptions ----------
    UPDATE public.subscriptions
    SET plan_id = v_free_plan_id,
        updated_at = NOW()
    WHERE tier = 'free'
      AND (plan_id IS NULL OR plan_id <> v_free_plan_id);
    GET DIAGNOSTICS v_subs_linked = ROW_COUNT;
    RAISE NOTICE 'Subscriptions linked to free plan: %', v_subs_linked;

    -- Pre-count for visibility
    SELECT COUNT(*) INTO v_free_users
    FROM public.subscriptions WHERE tier = 'free';
    RAISE NOTICE 'Total free-tier users: %', v_free_users;

    SELECT COUNT(*) INTO v_free_drafts_existing
    FROM public.websites w
    JOIN public.subscriptions s ON s.user_id = w.user_id
    WHERE s.tier = 'free' AND w.status = 'draft';
    RAISE NOTICE 'Free-tier websites already in draft (no change): %', v_free_drafts_existing;

    -- ---------- STEP 3: Backfill usage_tracking ----------
    -- Add a usage_tracking row for the current billing period for any free
    -- user who doesn't have one. Uses TO_CHAR for YYYY-MM.
    INSERT INTO public.usage_tracking (user_id, billing_period, websites_count)
    SELECT
        s.user_id,
        TO_CHAR(NOW(), 'YYYY-MM'),
        COALESCE((SELECT COUNT(*) FROM public.websites w WHERE w.user_id = s.user_id), 0)
    FROM public.subscriptions s
    WHERE s.tier = 'free'
      AND NOT EXISTS (
          SELECT 1 FROM public.usage_tracking u
          WHERE u.user_id = s.user_id
            AND u.billing_period = TO_CHAR(NOW(), 'YYYY-MM')
      );
    GET DIAGNOSTICS v_usage_added = ROW_COUNT;
    RAISE NOTICE 'usage_tracking rows backfilled: %', v_usage_added;

    -- ---------- STEP 4: Force free-tier websites back to draft ----------
    -- Idempotent: WHERE status = 'published' skips already-draft rows.
    UPDATE public.websites w
    SET status = 'draft',
        public_url = NULL,
        published_at = NULL,
        updated_at = NOW()
    FROM public.subscriptions s
    WHERE w.user_id = s.user_id
      AND s.tier = 'free'
      AND w.status = 'published';
    GET DIAGNOSTICS v_sites_drafted = ROW_COUNT;
    RAISE NOTICE 'Free-tier websites forced to draft: %', v_sites_drafted;

    RAISE NOTICE '----------------------------------------';
    RAISE NOTICE 'Migration 025 complete.';
END $$;

COMMIT;

-- ==========================================================================
-- DOWN MIGRATION (manual, copy-paste to revert)
-- ==========================================================================
-- BEGIN;
-- UPDATE public.subscriptions SET plan_id = NULL
--   WHERE plan_id = (SELECT plan_id FROM public.subscription_plans WHERE plan_name = 'free');
-- DELETE FROM public.subscription_plans WHERE plan_name = 'free';
-- -- Note: usage_tracking rows and websites status changes are NOT reverted
-- --       (websites going from draft back to published is unsafe — the
-- --        storage HTML may have been altered or removed).
-- COMMIT;

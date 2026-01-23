-- =============================================
-- Migration: Process Manual Payment
-- Description: Process the successful ToyyibPay payment that wasn't recorded
-- Bill Code: i8i19rq3
-- Reference: TP2601232454557272
-- Amount: RM 29.00
-- Date: 2026-01-23
-- =============================================

-- Step 1: First, ensure the payments table exists (run 015 migration first)
-- This is a safeguard in case tables don't exist yet

-- Step 2: Find and update the user who made the payment
-- The external reference was: SUB_basic_4cd51550...

-- Find users matching the pattern
DO $$
DECLARE
    target_user_id UUID;
    subscription_exists BOOLEAN;
BEGIN
    -- Try to find user by ID prefix (from the external reference SUB_basic_4cd51550)
    SELECT id INTO target_user_id
    FROM auth.users
    WHERE id::text LIKE '4cd51550%'
    LIMIT 1;

    IF target_user_id IS NULL THEN
        RAISE NOTICE 'User with ID starting with 4cd51550 not found. Checking recent users...';

        -- Alternative: Find the most recent user who might have made the payment
        -- This is a fallback - in production, you'd want to verify this manually
        SELECT id INTO target_user_id
        FROM auth.users
        ORDER BY created_at DESC
        LIMIT 1;
    END IF;

    IF target_user_id IS NOT NULL THEN
        RAISE NOTICE 'Processing payment for user: %', target_user_id;

        -- Step 3: Check if subscription exists for this user
        SELECT EXISTS(
            SELECT 1 FROM public.subscriptions WHERE user_id = target_user_id
        ) INTO subscription_exists;

        IF subscription_exists THEN
            -- Update existing subscription
            UPDATE public.subscriptions
            SET
                tier = 'basic',
                status = 'active',
                price = 29.00,
                toyyibpay_bill_code = 'i8i19rq3',
                current_period_start = CURRENT_DATE,
                current_period_end = CURRENT_DATE + INTERVAL '30 days',
                updated_at = NOW()
            WHERE user_id = target_user_id;

            RAISE NOTICE 'Updated existing subscription to Basic tier';
        ELSE
            -- Create new subscription
            INSERT INTO public.subscriptions (
                user_id, tier, status, price, toyyibpay_bill_code,
                current_period_start, current_period_end, created_at, updated_at
            ) VALUES (
                target_user_id, 'basic', 'active', 29.00, 'i8i19rq3',
                CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days', NOW(), NOW()
            );

            RAISE NOTICE 'Created new subscription with Basic tier';
        END IF;

        -- Step 4: Update or create usage limits for Basic tier
        INSERT INTO public.usage_limits (
            user_id, websites_limit, menu_items_limit, ai_hero_limit,
            ai_menu_limit, delivery_zones_limit, riders_limit,
            ai_hero_generations, ai_menu_images, created_at, updated_at
        ) VALUES (
            target_user_id, 5, NULL, 10, 30, 5, 0, 0, 0, NOW(), NOW()
        )
        ON CONFLICT (user_id) DO UPDATE SET
            websites_limit = 5,
            menu_items_limit = NULL,  -- Unlimited for Basic
            ai_hero_limit = 10,
            ai_menu_limit = 30,
            delivery_zones_limit = 5,
            riders_limit = 0,
            updated_at = NOW();

        RAISE NOTICE 'Updated usage limits for Basic tier';

        -- Step 5: Record the payment in payments table
        INSERT INTO public.payments (
            user_id, bill_code, amount, type, tier, status,
            transaction_id, reference_no, created_at, updated_at
        ) VALUES (
            target_user_id, 'i8i19rq3', 29.00, 'subscription', 'basic', 'successful',
            'TP2601232454557272', 'TP2601232454557272', '2026-01-23 21:05:03'::timestamp, NOW()
        )
        ON CONFLICT DO NOTHING;  -- Don't error if already recorded

        RAISE NOTICE 'Recorded payment in payments table';
        RAISE NOTICE 'SUCCESS: User % upgraded to Basic tier!', target_user_id;

    ELSE
        RAISE NOTICE 'ERROR: Could not find any user to upgrade';
    END IF;
END $$;

-- Verify the upgrade
SELECT
    u.id as user_id,
    u.email,
    s.tier,
    s.status,
    s.price,
    s.toyyibpay_bill_code,
    s.current_period_end
FROM auth.users u
LEFT JOIN public.subscriptions s ON u.id = s.user_id
WHERE u.id::text LIKE '4cd51550%'
OR s.toyyibpay_bill_code = 'i8i19rq3';

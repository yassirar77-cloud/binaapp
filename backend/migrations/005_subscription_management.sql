-- ==========================================================================
-- BINAAPP SUBSCRIPTION MANAGEMENT SYSTEM
-- Migration: 005_subscription_management.sql
-- Created: 2026-01-23
-- ==========================================================================

-- ==========================================================================
-- SECTION 1: SUBSCRIPTION PLANS TABLE
-- ==========================================================================

-- Drop existing table if exists to recreate with proper structure
DROP TABLE IF EXISTS public.subscription_plans CASCADE;

CREATE TABLE public.subscription_plans (
    plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_name TEXT NOT NULL UNIQUE, -- 'starter', 'basic', 'pro'
    display_name TEXT NOT NULL, -- 'Starter', 'Basic', 'Pro'
    price DECIMAL(10,2) NOT NULL,
    websites_limit INTEGER, -- NULL = unlimited
    menu_items_limit INTEGER, -- NULL = unlimited
    ai_hero_limit INTEGER, -- NULL = unlimited, monthly reset
    ai_images_limit INTEGER, -- NULL = unlimited, monthly reset
    delivery_zones_limit INTEGER, -- NULL = unlimited
    riders_limit INTEGER DEFAULT 0, -- 0 = not allowed, NULL = unlimited
    features JSONB DEFAULT '{}', -- Store feature flags
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default plans matching BinaApp pricing
INSERT INTO public.subscription_plans (plan_name, display_name, price, websites_limit, menu_items_limit, ai_hero_limit, ai_images_limit, delivery_zones_limit, riders_limit, features, sort_order) VALUES
    ('starter', 'Starter', 5.00, 1, 20, 1, 5, 1, 0,
     '{"subdomain": true, "all_integrations": true, "email_support": true, "custom_domain": false, "priority_ai": false, "analytics": false, "qr_payment": false, "api_access": false, "white_label": false}',
     1),
    ('basic', 'Basic', 29.00, 5, NULL, 10, 30, 5, 0,
     '{"subdomain": true, "custom_subdomain": true, "all_integrations": true, "priority_support": true, "priority_ai": true, "analytics": true, "qr_payment": true, "contact_form": true, "custom_domain": false, "api_access": false, "white_label": false}',
     2),
    ('pro', 'Pro', 49.00, NULL, NULL, NULL, NULL, NULL, 10,
     '{"subdomain": true, "custom_subdomain": true, "custom_domain": true, "all_integrations": true, "priority_support": true, "advanced_ai": true, "analytics": true, "qr_payment": true, "contact_form": true, "api_access": true, "white_label": true, "gps_tracking": true}',
     3)
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
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();

-- RLS for subscription_plans (readable by everyone)
ALTER TABLE public.subscription_plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view subscription plans" ON public.subscription_plans
    FOR SELECT USING (is_active = true);

-- ==========================================================================
-- SECTION 2: UPDATE SUBSCRIPTIONS TABLE
-- ==========================================================================

-- Add new columns to existing subscriptions table
ALTER TABLE public.subscriptions
    ADD COLUMN IF NOT EXISTS plan_id UUID REFERENCES public.subscription_plans(plan_id),
    ADD COLUMN IF NOT EXISTS start_date TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS end_date TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
    ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS toyyibpay_bill_code TEXT,
    ADD COLUMN IF NOT EXISTS price DECIMAL(10,2) DEFAULT 0;

-- Update tier column to use new naming if needed
-- Map old tier names to new ones
UPDATE public.subscriptions
SET tier = CASE
    WHEN tier = 'free' THEN 'starter'
    WHEN tier IN ('starter', 'basic', 'pro') THEN tier
    ELSE 'starter'
END;

-- Link existing subscriptions to plan_id
UPDATE public.subscriptions s
SET plan_id = p.plan_id
FROM public.subscription_plans p
WHERE s.tier = p.plan_name AND s.plan_id IS NULL;

-- ==========================================================================
-- SECTION 3: USAGE TRACKING TABLE
-- ==========================================================================

DROP TABLE IF EXISTS public.usage_tracking CASCADE;

CREATE TABLE public.usage_tracking (
    usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    billing_period TEXT NOT NULL, -- 'YYYY-MM' format

    -- Resource counts
    websites_count INTEGER DEFAULT 0,
    menu_items_count INTEGER DEFAULT 0,
    ai_hero_used INTEGER DEFAULT 0,
    ai_images_used INTEGER DEFAULT 0,
    delivery_zones_count INTEGER DEFAULT 0,
    riders_count INTEGER DEFAULT 0,

    -- Additional addon usage
    addon_websites_used INTEGER DEFAULT 0,
    addon_ai_hero_used INTEGER DEFAULT 0,
    addon_ai_images_used INTEGER DEFAULT 0,
    addon_riders_used INTEGER DEFAULT 0,
    addon_zones_used INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, billing_period)
);

CREATE INDEX idx_usage_tracking_user ON public.usage_tracking(user_id);
CREATE INDEX idx_usage_tracking_period ON public.usage_tracking(billing_period);

ALTER TABLE public.usage_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own usage" ON public.usage_tracking
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all usage" ON public.usage_tracking
    FOR ALL USING (true);

-- ==========================================================================
-- SECTION 4: TRANSACTIONS TABLE
-- ==========================================================================

DROP TABLE IF EXISTS public.transactions CASCADE;

CREATE TABLE public.transactions (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    transaction_type TEXT NOT NULL, -- 'subscription', 'addon', 'renewal'
    item_description TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,

    -- ToyyibPay details
    toyyibpay_bill_code TEXT,
    toyyibpay_transaction_id TEXT,
    payment_status TEXT DEFAULT 'pending', -- 'pending', 'success', 'failed'
    payment_date TIMESTAMPTZ,

    -- Invoice
    invoice_number TEXT,

    -- Additional details
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_user ON public.transactions(user_id);
CREATE INDEX idx_transactions_status ON public.transactions(payment_status);
CREATE INDEX idx_transactions_date ON public.transactions(created_at DESC);
CREATE INDEX idx_transactions_bill_code ON public.transactions(toyyibpay_bill_code);

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own transactions" ON public.transactions
    FOR SELECT USING (auth.uid() = user_id);

-- Generate invoice number function
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS TEXT AS $$
DECLARE
    new_number TEXT;
    counter INTEGER;
BEGIN
    SELECT COUNT(*) INTO counter
    FROM public.transactions
    WHERE DATE(created_at) = CURRENT_DATE;

    new_number := 'INV-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD((counter + 1)::TEXT, 4, '0');

    RETURN new_number;
END;
$$ LANGUAGE plpgsql;

-- Auto-fill invoice_number if missing
CREATE OR REPLACE FUNCTION transactions_set_invoice_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.invoice_number IS NULL OR NEW.invoice_number = '' THEN
        NEW.invoice_number := generate_invoice_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_transactions_set_invoice_number ON public.transactions;
CREATE TRIGGER trg_transactions_set_invoice_number
    BEFORE INSERT ON public.transactions
    FOR EACH ROW
    EXECUTE FUNCTION transactions_set_invoice_number();

-- ==========================================================================
-- SECTION 5: ADDON PURCHASES TABLE
-- ==========================================================================

DROP TABLE IF EXISTS public.addon_purchases CASCADE;

CREATE TABLE public.addon_purchases (
    addon_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    transaction_id UUID REFERENCES public.transactions(transaction_id),

    addon_type TEXT NOT NULL, -- 'ai_image', 'ai_hero', 'website', 'rider', 'zone'
    quantity INTEGER NOT NULL DEFAULT 1,
    quantity_used INTEGER DEFAULT 0,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,

    status TEXT DEFAULT 'active', -- 'active', 'depleted', 'expired'
    expires_at TIMESTAMPTZ, -- Some addons might expire

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_addon_purchases_user ON public.addon_purchases(user_id);
CREATE INDEX idx_addon_purchases_type ON public.addon_purchases(addon_type);
CREATE INDEX idx_addon_purchases_status ON public.addon_purchases(status);

ALTER TABLE public.addon_purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own addon purchases" ON public.addon_purchases
    FOR SELECT USING (auth.uid() = user_id);

-- ==========================================================================
-- SECTION 6: ADDON PRICING TABLE
-- ==========================================================================

DROP TABLE IF EXISTS public.addon_pricing CASCADE;

CREATE TABLE public.addon_pricing (
    pricing_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    addon_type TEXT NOT NULL UNIQUE,
    addon_name TEXT NOT NULL,
    description TEXT,
    unit_price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert addon pricing
INSERT INTO public.addon_pricing (addon_type, addon_name, description, unit_price) VALUES
    ('ai_image', 'AI Image Generation', 'Generate 1 AI menu image', 0.50),
    ('ai_hero', 'AI Hero Generation', 'Generate 1 AI hero section', 2.00),
    ('website', 'Extra Website', 'Add 1 additional website slot', 5.00),
    ('rider', 'Extra Rider', 'Add 1 additional rider slot', 3.00),
    ('zone', 'Extra Delivery Zone', 'Add 1 additional delivery zone', 2.00)
ON CONFLICT (addon_type) DO UPDATE SET
    addon_name = EXCLUDED.addon_name,
    description = EXCLUDED.description,
    unit_price = EXCLUDED.unit_price;

ALTER TABLE public.addon_pricing ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view addon pricing" ON public.addon_pricing
    FOR SELECT USING (is_active = true);

-- ==========================================================================
-- SECTION 7: SUBSCRIPTION REMINDERS TABLE
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.subscription_reminders (
    reminder_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    subscription_id UUID REFERENCES public.subscriptions(id) ON DELETE CASCADE,
    reminder_type TEXT NOT NULL, -- '7_days', '3_days', '1_day', 'expired'
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    email_sent BOOLEAN DEFAULT false,

    UNIQUE(user_id, subscription_id, reminder_type)
);

CREATE INDEX idx_reminders_user ON public.subscription_reminders(user_id);

ALTER TABLE public.subscription_reminders ENABLE ROW LEVEL SECURITY;

-- ==========================================================================
-- SECTION 8: HELPER FUNCTIONS
-- ==========================================================================

-- Function to get current billing period
CREATE OR REPLACE FUNCTION get_current_billing_period()
RETURNS TEXT AS $$
BEGIN
    RETURN TO_CHAR(NOW(), 'YYYY-MM');
END;
$$ LANGUAGE plpgsql;

-- Function to initialize or get usage tracking for a user
CREATE OR REPLACE FUNCTION get_or_create_usage_tracking(p_user_id UUID)
RETURNS public.usage_tracking AS $$
DECLARE
    v_record public.usage_tracking;
    v_billing_period TEXT;
BEGIN
    v_billing_period := get_current_billing_period();

    SELECT * INTO v_record
    FROM public.usage_tracking
    WHERE user_id = p_user_id AND billing_period = v_billing_period;

    IF NOT FOUND THEN
        INSERT INTO public.usage_tracking (user_id, billing_period)
        VALUES (p_user_id, v_billing_period)
        RETURNING * INTO v_record;
    END IF;

    RETURN v_record;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's subscription limits
CREATE OR REPLACE FUNCTION get_user_limits(p_user_id UUID)
RETURNS TABLE (
    plan_name TEXT,
    websites_limit INTEGER,
    menu_items_limit INTEGER,
    ai_hero_limit INTEGER,
    ai_images_limit INTEGER,
    delivery_zones_limit INTEGER,
    riders_limit INTEGER,
    features JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sp.plan_name,
        sp.websites_limit,
        sp.menu_items_limit,
        sp.ai_hero_limit,
        sp.ai_images_limit,
        sp.delivery_zones_limit,
        sp.riders_limit,
        sp.features
    FROM public.subscriptions s
    JOIN public.subscription_plans sp ON s.plan_id = sp.plan_id OR s.tier = sp.plan_name
    WHERE s.user_id = p_user_id AND s.status = 'active'
    LIMIT 1;

    -- If no active subscription, return starter limits
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT
            sp.plan_name,
            sp.websites_limit,
            sp.menu_items_limit,
            sp.ai_hero_limit,
            sp.ai_images_limit,
            sp.delivery_zones_limit,
            sp.riders_limit,
            sp.features
        FROM public.subscription_plans sp
        WHERE sp.plan_name = 'starter'
        LIMIT 1;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user can perform action
CREATE OR REPLACE FUNCTION check_user_limit(
    p_user_id UUID,
    p_action TEXT
)
RETURNS TABLE (
    allowed BOOLEAN,
    current_usage INTEGER,
    plan_limit INTEGER,
    is_unlimited BOOLEAN,
    addon_available INTEGER,
    addon_price DECIMAL(10,2),
    message TEXT
) AS $$
DECLARE
    v_usage public.usage_tracking;
    v_limits RECORD;
    v_addon_count INTEGER;
    v_addon_type TEXT;
    v_addon_price DECIMAL(10,2);
    v_current INTEGER;
    v_limit INTEGER;
BEGIN
    -- Get or create usage tracking
    SELECT * INTO v_usage FROM get_or_create_usage_tracking(p_user_id);

    -- Get user limits
    SELECT * INTO v_limits FROM get_user_limits(p_user_id);

    -- Map action to addon type
    v_addon_type := CASE p_action
        WHEN 'create_website' THEN 'website'
        WHEN 'generate_ai_hero' THEN 'ai_hero'
        WHEN 'generate_ai_image' THEN 'ai_image'
        WHEN 'add_zone' THEN 'zone'
        WHEN 'add_rider' THEN 'rider'
        ELSE NULL
    END;

    -- Get addon price
    SELECT unit_price INTO v_addon_price
    FROM public.addon_pricing
    WHERE addon_type = v_addon_type;

    -- Get available addon credits
    SELECT COALESCE(SUM(quantity - quantity_used), 0) INTO v_addon_count
    FROM public.addon_purchases
    WHERE user_id = p_user_id
      AND addon_type = v_addon_type
      AND status = 'active'
      AND (expires_at IS NULL OR expires_at > NOW());

    -- Determine current usage and limit based on action
    CASE p_action
        WHEN 'create_website' THEN
            v_current := v_usage.websites_count;
            v_limit := v_limits.websites_limit;
        WHEN 'add_menu_item' THEN
            v_current := v_usage.menu_items_count;
            v_limit := v_limits.menu_items_limit;
        WHEN 'generate_ai_hero' THEN
            v_current := v_usage.ai_hero_used;
            v_limit := v_limits.ai_hero_limit;
        WHEN 'generate_ai_image' THEN
            v_current := v_usage.ai_images_used;
            v_limit := v_limits.ai_images_limit;
        WHEN 'add_zone' THEN
            v_current := v_usage.delivery_zones_count;
            v_limit := v_limits.delivery_zones_limit;
        WHEN 'add_rider' THEN
            v_current := v_usage.riders_count;
            v_limit := v_limits.riders_limit;
        ELSE
            v_current := 0;
            v_limit := NULL;
    END CASE;

    -- Check if unlimited
    IF v_limit IS NULL THEN
        RETURN QUERY SELECT
            TRUE,
            v_current,
            v_limit,
            TRUE,
            v_addon_count,
            v_addon_price,
            'Unlimited'::TEXT;
        RETURN;
    END IF;

    -- Check if within limit
    IF v_current < v_limit THEN
        RETURN QUERY SELECT
            TRUE,
            v_current,
            v_limit,
            FALSE,
            v_addon_count,
            v_addon_price,
            'Within limit'::TEXT;
        RETURN;
    END IF;

    -- Check if has addon credits
    IF v_addon_count > 0 THEN
        RETURN QUERY SELECT
            TRUE,
            v_current,
            v_limit,
            FALSE,
            v_addon_count,
            v_addon_price,
            'Using addon credit'::TEXT;
        RETURN;
    END IF;

    -- Limit reached
    RETURN QUERY SELECT
        FALSE,
        v_current,
        v_limit,
        FALSE,
        v_addon_count,
        v_addon_price,
        'Limit reached. Upgrade or buy addon.'::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to increment usage
CREATE OR REPLACE FUNCTION increment_usage(
    p_user_id UUID,
    p_action TEXT,
    p_count INTEGER DEFAULT 1
)
RETURNS BOOLEAN AS $$
DECLARE
    v_billing_period TEXT;
BEGIN
    v_billing_period := get_current_billing_period();

    -- Ensure usage record exists
    PERFORM get_or_create_usage_tracking(p_user_id);

    -- Update the appropriate counter
    CASE p_action
        WHEN 'create_website' THEN
            UPDATE public.usage_tracking
            SET websites_count = websites_count + p_count, updated_at = NOW()
            WHERE user_id = p_user_id AND billing_period = v_billing_period;
        WHEN 'add_menu_item' THEN
            UPDATE public.usage_tracking
            SET menu_items_count = menu_items_count + p_count, updated_at = NOW()
            WHERE user_id = p_user_id AND billing_period = v_billing_period;
        WHEN 'generate_ai_hero' THEN
            UPDATE public.usage_tracking
            SET ai_hero_used = ai_hero_used + p_count, updated_at = NOW()
            WHERE user_id = p_user_id AND billing_period = v_billing_period;
        WHEN 'generate_ai_image' THEN
            UPDATE public.usage_tracking
            SET ai_images_used = ai_images_used + p_count, updated_at = NOW()
            WHERE user_id = p_user_id AND billing_period = v_billing_period;
        WHEN 'add_zone' THEN
            UPDATE public.usage_tracking
            SET delivery_zones_count = delivery_zones_count + p_count, updated_at = NOW()
            WHERE user_id = p_user_id AND billing_period = v_billing_period;
        WHEN 'add_rider' THEN
            UPDATE public.usage_tracking
            SET riders_count = riders_count + p_count, updated_at = NOW()
            WHERE user_id = p_user_id AND billing_period = v_billing_period;
        ELSE
            RETURN FALSE;
    END CASE;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to use addon credit
CREATE OR REPLACE FUNCTION use_addon_credit(
    p_user_id UUID,
    p_addon_type TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_addon_id UUID;
BEGIN
    -- Find an active addon with available credits
    SELECT addon_id INTO v_addon_id
    FROM public.addon_purchases
    WHERE user_id = p_user_id
      AND addon_type = p_addon_type
      AND status = 'active'
      AND quantity_used < quantity
      AND (expires_at IS NULL OR expires_at > NOW())
    ORDER BY created_at ASC
    LIMIT 1
    FOR UPDATE;

    IF v_addon_id IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Use one credit
    UPDATE public.addon_purchases
    SET quantity_used = quantity_used + 1,
        status = CASE WHEN quantity_used + 1 >= quantity THEN 'depleted' ELSE 'active' END
    WHERE addon_id = v_addon_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================================================
-- SECTION 9: TRIGGERS
-- ==========================================================================

-- Trigger to update usage tracking timestamp
CREATE TRIGGER update_usage_tracking_updated_at
    BEFORE UPDATE ON public.usage_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update subscription plans timestamp
CREATE TRIGGER update_subscription_plans_updated_at
    BEFORE UPDATE ON public.subscription_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================================================
-- SECTION 10: PERMISSIONS
-- ==========================================================================

GRANT SELECT ON public.subscription_plans TO authenticated;
GRANT SELECT ON public.addon_pricing TO authenticated;
GRANT SELECT ON public.usage_tracking TO authenticated;
GRANT SELECT ON public.transactions TO authenticated;
GRANT SELECT ON public.addon_purchases TO authenticated;

GRANT ALL ON public.subscription_plans TO service_role;
GRANT ALL ON public.addon_pricing TO service_role;
GRANT ALL ON public.usage_tracking TO service_role;
GRANT ALL ON public.transactions TO service_role;
GRANT ALL ON public.addon_purchases TO service_role;
GRANT ALL ON public.subscription_reminders TO service_role;

-- Allow anon users to view plans and pricing
GRANT SELECT ON public.subscription_plans TO anon;
GRANT SELECT ON public.addon_pricing TO anon;

-- ==========================================================================
-- SUCCESS MESSAGE
-- ==========================================================================

DO $$
BEGIN
    RAISE NOTICE '=== BinaApp Subscription Management Migration Complete ===';
    RAISE NOTICE 'Tables created/updated:';
    RAISE NOTICE '  - subscription_plans (with starter, basic, pro plans)';
    RAISE NOTICE '  - subscriptions (updated with new columns)';
    RAISE NOTICE '  - usage_tracking (monthly usage per user)';
    RAISE NOTICE '  - transactions (payment history)';
    RAISE NOTICE '  - addon_purchases (addon credits)';
    RAISE NOTICE '  - addon_pricing (addon prices)';
    RAISE NOTICE '  - subscription_reminders (expiry notifications)';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - get_current_billing_period()';
    RAISE NOTICE '  - get_or_create_usage_tracking()';
    RAISE NOTICE '  - get_user_limits()';
    RAISE NOTICE '  - check_user_limit()';
    RAISE NOTICE '  - increment_usage()';
    RAISE NOTICE '  - use_addon_credit()';
END $$;

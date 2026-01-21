-- Migration: 015_subscription_system.sql
-- Description: Add subscription, payment, usage limits, and addon tables
-- BinaApp Pricing: Starter (RM5), Basic (RM29), Pro (RM49)

-- ==========================================
-- SUBSCRIPTIONS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    tier VARCHAR(20) DEFAULT 'starter' CHECK (tier IN ('starter', 'basic', 'pro')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired', 'pending')),
    price DECIMAL(10,2),
    billing_cycle VARCHAR(20) DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'yearly')),
    current_period_start DATE,
    current_period_end DATE,
    toyyibpay_bill_code VARCHAR(100),
    toyyibpay_subscription_id VARCHAR(100),
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ==========================================
-- PAYMENTS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    subscription_id INT REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_type VARCHAR(50) CHECK (payment_type IN ('subscription', 'addon', 'upgrade')),
    payment_method VARCHAR(50) DEFAULT 'toyyibpay',
    toyyibpay_bill_code VARCHAR(100),
    toyyibpay_payment_id VARCHAR(100),
    status VARCHAR(20) CHECK (status IN ('pending', 'successful', 'failed')),
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- USAGE LIMITS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS usage_limits (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    websites_count INT DEFAULT 0,
    websites_limit INT,
    menu_items_count INT DEFAULT 0,
    menu_items_limit INT,
    ai_hero_generations INT DEFAULT 0,
    ai_hero_limit INT,
    ai_menu_images INT DEFAULT 0,
    ai_menu_limit INT,
    delivery_zones_count INT DEFAULT 0,
    delivery_zones_limit INT,
    riders_count INT DEFAULT 0,
    riders_limit INT,
    current_period_start DATE,
    current_period_end DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ==========================================
-- ADDON PURCHASES TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS addon_purchases (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    addon_type VARCHAR(50) CHECK (addon_type IN ('website', 'delivery_zone', 'ai_hero', 'ai_image', 'rider')),
    quantity INT DEFAULT 1,
    price_per_unit DECIMAL(10,2),
    total_price DECIMAL(10,2),
    billing_start DATE,
    billing_end DATE,
    is_recurring BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired')),
    toyyibpay_bill_code VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==========================================
-- INDEXES
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON subscriptions(tier);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_subscription_id ON payments(subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_limits_user_id ON usage_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_addon_purchases_user_id ON addon_purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_addon_purchases_status ON addon_purchases(status);

-- ==========================================
-- TRIGGER: Update timestamp on subscription change
-- ==========================================
CREATE OR REPLACE FUNCTION update_subscription_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_subscription_timestamp
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_subscription_timestamp();

CREATE TRIGGER trigger_update_usage_limits_timestamp
    BEFORE UPDATE ON usage_limits
    FOR EACH ROW
    EXECUTE FUNCTION update_subscription_timestamp();

-- ==========================================
-- FUNCTION: Initialize user subscription on signup
-- ==========================================
CREATE OR REPLACE FUNCTION initialize_user_subscription()
RETURNS TRIGGER AS $$
BEGIN
    -- Create default Starter subscription
    INSERT INTO subscriptions (
        user_id,
        tier,
        price,
        current_period_start,
        current_period_end,
        status
    ) VALUES (
        NEW.id,
        'starter',
        5.00,
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '30 days',
        'active'
    );

    -- Initialize usage limits for Starter tier
    INSERT INTO usage_limits (
        user_id,
        websites_limit,
        menu_items_limit,
        ai_hero_limit,
        ai_menu_limit,
        delivery_zones_limit,
        riders_limit,
        current_period_start,
        current_period_end
    ) VALUES (
        NEW.id,
        1,    -- websites
        20,   -- menu items
        1,    -- AI hero (lifetime)
        5,    -- AI images (lifetime)
        1,    -- delivery zones
        0,    -- riders
        CURRENT_DATE,
        CURRENT_DATE + INTERVAL '30 days'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for new user signups
DROP TRIGGER IF EXISTS after_user_signup ON auth.users;
CREATE TRIGGER after_user_signup
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION initialize_user_subscription();

-- ==========================================
-- ROW LEVEL SECURITY POLICIES
-- ==========================================

-- Enable RLS on all tables
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE addon_purchases ENABLE ROW LEVEL SECURITY;

-- Subscriptions: Users can view/update their own subscription
CREATE POLICY "Users can view own subscription" ON subscriptions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own subscription" ON subscriptions
    FOR UPDATE USING (auth.uid() = user_id);

-- Service role can manage all subscriptions
CREATE POLICY "Service role manages subscriptions" ON subscriptions
    FOR ALL USING (auth.role() = 'service_role');

-- Payments: Users can view their own payments
CREATE POLICY "Users can view own payments" ON payments
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can manage all payments
CREATE POLICY "Service role manages payments" ON payments
    FOR ALL USING (auth.role() = 'service_role');

-- Usage Limits: Users can view their own usage
CREATE POLICY "Users can view own usage limits" ON usage_limits
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can manage all usage limits
CREATE POLICY "Service role manages usage limits" ON usage_limits
    FOR ALL USING (auth.role() = 'service_role');

-- Addon Purchases: Users can view their own addons
CREATE POLICY "Users can view own addon purchases" ON addon_purchases
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can manage all addon purchases
CREATE POLICY "Service role manages addon purchases" ON addon_purchases
    FOR ALL USING (auth.role() = 'service_role');

-- ==========================================
-- HELPER FUNCTION: Upgrade subscription
-- ==========================================
CREATE OR REPLACE FUNCTION upgrade_subscription(
    p_user_id UUID,
    p_new_tier VARCHAR(20),
    p_price DECIMAL(10,2)
)
RETURNS VOID AS $$
DECLARE
    v_websites_limit INT;
    v_menu_items_limit INT;
    v_ai_hero_limit INT;
    v_ai_menu_limit INT;
    v_delivery_zones_limit INT;
    v_riders_limit INT;
BEGIN
    -- Set limits based on tier
    CASE p_new_tier
        WHEN 'starter' THEN
            v_websites_limit := 1;
            v_menu_items_limit := 20;
            v_ai_hero_limit := 1;
            v_ai_menu_limit := 5;
            v_delivery_zones_limit := 1;
            v_riders_limit := 0;
        WHEN 'basic' THEN
            v_websites_limit := 5;
            v_menu_items_limit := NULL; -- unlimited
            v_ai_hero_limit := 10;
            v_ai_menu_limit := 30;
            v_delivery_zones_limit := 5;
            v_riders_limit := 0;
        WHEN 'pro' THEN
            v_websites_limit := NULL; -- unlimited
            v_menu_items_limit := NULL; -- unlimited
            v_ai_hero_limit := NULL; -- unlimited
            v_ai_menu_limit := NULL; -- unlimited
            v_delivery_zones_limit := NULL; -- unlimited
            v_riders_limit := 10;
    END CASE;

    -- Update subscription
    UPDATE subscriptions
    SET tier = p_new_tier,
        price = p_price,
        current_period_start = CURRENT_DATE,
        current_period_end = CURRENT_DATE + INTERVAL '30 days',
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- Update usage limits
    UPDATE usage_limits
    SET websites_limit = v_websites_limit,
        menu_items_limit = v_menu_items_limit,
        ai_hero_limit = v_ai_hero_limit,
        ai_menu_limit = v_ai_menu_limit,
        delivery_zones_limit = v_delivery_zones_limit,
        riders_limit = v_riders_limit,
        current_period_start = CURRENT_DATE,
        current_period_end = CURRENT_DATE + INTERVAL '30 days',
        updated_at = NOW()
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- HELPER FUNCTION: Reset monthly usage
-- ==========================================
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS VOID AS $$
BEGIN
    -- Reset usage counts for Basic and Pro users whose period has ended
    UPDATE usage_limits ul
    SET
        ai_hero_generations = 0,
        ai_menu_images = 0,
        current_period_start = CURRENT_DATE,
        current_period_end = CURRENT_DATE + INTERVAL '30 days',
        updated_at = NOW()
    FROM subscriptions s
    WHERE ul.user_id = s.user_id
      AND s.tier IN ('basic', 'pro')
      AND ul.current_period_end < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==========================================
-- COMMENTS
-- ==========================================
COMMENT ON TABLE subscriptions IS 'User subscription information for BinaApp (Starter RM5, Basic RM29, Pro RM49)';
COMMENT ON TABLE payments IS 'Payment history for subscriptions and addons via ToyyibPay';
COMMENT ON TABLE usage_limits IS 'Track user resource usage against their subscription limits';
COMMENT ON TABLE addon_purchases IS 'One-time or recurring addon purchases';
COMMENT ON FUNCTION initialize_user_subscription() IS 'Automatically creates Starter subscription for new users';
COMMENT ON FUNCTION upgrade_subscription(UUID, VARCHAR, DECIMAL) IS 'Upgrade user to a new subscription tier';
COMMENT ON FUNCTION reset_monthly_usage() IS 'Reset AI generation counts for paid tiers (run via cron)';

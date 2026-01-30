-- ==========================================================================
-- BINAAPP SUBSCRIPTION LOCK SYSTEM
-- Migration: 002_subscription_lock_system.sql
-- Created: 2026-01-30
-- ==========================================================================
-- PURPOSE:
-- This migration adds subscription expiry and lock functionality to BinaApp.
-- When subscriptions expire, users enter a grace period before full lock.
--
-- LOCK FLOW:
-- 1. 'active' - Paid and valid subscription
-- 2. 'expired' - Past end_date, entering grace period
-- 3. 'grace' - 5-day warning period before lock
-- 4. 'locked' - Full lock, must pay to unlock
--
-- EXISTING USERS: Get 14 days free before any locking applies
-- ==========================================================================

-- ==========================================================================
-- SECTION 1: ALTER SUBSCRIPTIONS TABLE - ADD NEW COLUMNS
-- ==========================================================================
-- Adding columns for lock functionality to existing subscriptions table.
-- Using DO block with IF NOT EXISTS pattern for safety.

DO $$
BEGIN
    -- Add grace_period_end column (nullable)
    -- Stores when the grace period ends and full lock begins
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'subscriptions'
        AND column_name = 'grace_period_end'
    ) THEN
        ALTER TABLE public.subscriptions ADD COLUMN grace_period_end TIMESTAMPTZ;
        RAISE NOTICE 'Added column: grace_period_end';
    END IF;

    -- Add lock_reason column (nullable)
    -- Stores reason for lock: 'payment_failed', 'subscription_expired', 'manual', etc.
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'subscriptions'
        AND column_name = 'lock_reason'
    ) THEN
        ALTER TABLE public.subscriptions ADD COLUMN lock_reason TEXT;
        RAISE NOTICE 'Added column: lock_reason';
    END IF;

    -- Add last_payment_reminder column (nullable)
    -- Tracks when last payment reminder was sent
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'subscriptions'
        AND column_name = 'last_payment_reminder'
    ) THEN
        ALTER TABLE public.subscriptions ADD COLUMN last_payment_reminder TIMESTAMPTZ;
        RAISE NOTICE 'Added column: last_payment_reminder';
    END IF;

    -- Add locked_at column (nullable)
    -- Timestamp when subscription was locked
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'subscriptions'
        AND column_name = 'locked_at'
    ) THEN
        ALTER TABLE public.subscriptions ADD COLUMN locked_at TIMESTAMPTZ;
        RAISE NOTICE 'Added column: locked_at';
    END IF;
END $$;

-- ==========================================================================
-- SECTION 2: UPDATE STATUS CHECK CONSTRAINT
-- ==========================================================================
-- Drop existing constraint (if any) and recreate with new allowed values.
-- New status values: 'active', 'expired', 'grace', 'locked', 'cancelled'

DO $$
DECLARE
    constraint_exists BOOLEAN;
BEGIN
    -- Check if a constraint exists on the status column
    SELECT EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage ccu
        JOIN information_schema.table_constraints tc
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_schema = 'public'
        AND tc.table_name = 'subscriptions'
        AND ccu.column_name = 'status'
        AND tc.constraint_type = 'CHECK'
    ) INTO constraint_exists;

    -- Drop existing check constraint if found
    IF constraint_exists THEN
        -- Find and drop all check constraints on status column
        EXECUTE (
            SELECT string_agg('ALTER TABLE public.subscriptions DROP CONSTRAINT IF EXISTS ' || quote_ident(tc.constraint_name), '; ')
            FROM information_schema.constraint_column_usage ccu
            JOIN information_schema.table_constraints tc
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.table_schema = 'public'
            AND tc.table_name = 'subscriptions'
            AND ccu.column_name = 'status'
            AND tc.constraint_type = 'CHECK'
        );
        RAISE NOTICE 'Dropped existing status check constraint(s)';
    END IF;
END $$;

-- Add new check constraint with all subscription status values
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'subscriptions_status_check'
        AND table_name = 'subscriptions'
    ) THEN
        ALTER TABLE public.subscriptions
        ADD CONSTRAINT subscriptions_status_check
        CHECK (status IN ('active', 'expired', 'grace', 'locked', 'cancelled', 'pending'));
        RAISE NOTICE 'Added new status check constraint';
    END IF;
EXCEPTION WHEN duplicate_object THEN
    RAISE NOTICE 'Status check constraint already exists';
END $$;

-- ==========================================================================
-- SECTION 3: CREATE SUBSCRIPTION EMAIL LOGS TABLE
-- ==========================================================================
-- Tracks all subscription-related emails sent to users.
-- Prevents duplicate emails and provides audit trail.

CREATE TABLE IF NOT EXISTS public.subscription_email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES public.subscriptions(id) ON DELETE CASCADE,
    email_type TEXT NOT NULL,  -- 'reminder_5_days', 'expired', 'lock_warning', 'locked', 'unlocked'
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    email_address TEXT,  -- Store email address at time of sending
    metadata JSONB DEFAULT '{}',  -- Additional info like template used, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add check constraint for email_type values
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'subscription_email_logs_type_check'
        AND table_name = 'subscription_email_logs'
    ) THEN
        ALTER TABLE public.subscription_email_logs
        ADD CONSTRAINT subscription_email_logs_type_check
        CHECK (email_type IN (
            'reminder_5_days',    -- 5 days before expiry
            'reminder_3_days',    -- 3 days before expiry
            'reminder_1_day',     -- 1 day before expiry
            'expired',            -- Subscription has expired
            'grace_started',      -- Grace period has started
            'lock_warning',       -- Warning before lock
            'locked',             -- Account has been locked
            'unlocked',           -- Account has been unlocked
            'payment_failed',     -- Payment failed notification
            'payment_success'     -- Payment success confirmation
        ));
        RAISE NOTICE 'Added email_type check constraint';
    END IF;
EXCEPTION WHEN duplicate_object THEN
    RAISE NOTICE 'Email type check constraint already exists';
END $$;

-- Create index for efficient lookup by user and type
CREATE INDEX IF NOT EXISTS idx_subscription_email_logs_user_id
    ON public.subscription_email_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_subscription_email_logs_subscription_id
    ON public.subscription_email_logs(subscription_id);

CREATE INDEX IF NOT EXISTS idx_subscription_email_logs_email_type
    ON public.subscription_email_logs(email_type);

-- Composite index for checking recent emails
CREATE INDEX IF NOT EXISTS idx_subscription_email_logs_user_type_sent
    ON public.subscription_email_logs(user_id, email_type, sent_at DESC);

-- Enable RLS
ALTER TABLE public.subscription_email_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies
DROP POLICY IF EXISTS "Users can view their own email logs" ON public.subscription_email_logs;
CREATE POLICY "Users can view their own email logs"
    ON public.subscription_email_logs FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all email logs" ON public.subscription_email_logs;
CREATE POLICY "Service role can manage all email logs"
    ON public.subscription_email_logs FOR ALL
    USING (true);

-- Grant permissions
GRANT SELECT ON public.subscription_email_logs TO authenticated;
GRANT ALL ON public.subscription_email_logs TO service_role;

COMMENT ON TABLE public.subscription_email_logs IS 'Tracks subscription-related emails sent to users for audit and deduplication';

-- ==========================================================================
-- SECTION 4: CREATE WEBSITE LOCK STATUS TABLE
-- ==========================================================================
-- Tracks which websites are currently locked due to subscription issues.
-- Allows granular control over website access during lock periods.

CREATE TABLE IF NOT EXISTS public.website_lock_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    is_locked BOOLEAN NOT NULL DEFAULT false,
    locked_at TIMESTAMPTZ,
    lock_reason TEXT,  -- 'subscription_expired', 'subscription_locked', 'manual', 'payment_failed'
    unlocked_at TIMESTAMPTZ,
    unlocked_by TEXT,  -- 'payment', 'admin', 'system'
    lock_message TEXT,  -- Custom message shown on locked website
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one record per website
    UNIQUE(website_id)
);

-- Add check constraint for lock_reason values
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'website_lock_status_reason_check'
        AND table_name = 'website_lock_status'
    ) THEN
        ALTER TABLE public.website_lock_status
        ADD CONSTRAINT website_lock_status_reason_check
        CHECK (lock_reason IS NULL OR lock_reason IN (
            'subscription_expired',
            'subscription_locked',
            'subscription_grace',
            'payment_failed',
            'manual',
            'admin'
        ));
        RAISE NOTICE 'Added lock_reason check constraint';
    END IF;
EXCEPTION WHEN duplicate_object THEN
    RAISE NOTICE 'Lock reason check constraint already exists';
END $$;

-- ==========================================================================
-- SECTION 5: CREATE INDEXES FOR PERFORMANCE
-- ==========================================================================

-- Index on subscriptions for status and end_date queries
-- Used by cron jobs to find expiring/expired subscriptions
CREATE INDEX IF NOT EXISTS idx_subscriptions_status_end_date
    ON public.subscriptions(status, end_date);

-- Index for finding subscriptions by status alone
CREATE INDEX IF NOT EXISTS idx_subscriptions_status
    ON public.subscriptions(status);

-- Index for finding subscriptions nearing grace period end
CREATE INDEX IF NOT EXISTS idx_subscriptions_grace_period_end
    ON public.subscriptions(grace_period_end)
    WHERE grace_period_end IS NOT NULL;

-- Index for locked subscriptions
CREATE INDEX IF NOT EXISTS idx_subscriptions_locked_at
    ON public.subscriptions(locked_at)
    WHERE locked_at IS NOT NULL;

-- Index on website_lock_status for website_id lookups
CREATE INDEX IF NOT EXISTS idx_website_lock_status_website_id
    ON public.website_lock_status(website_id);

-- Index on website_lock_status for finding locked websites
CREATE INDEX IF NOT EXISTS idx_website_lock_status_is_locked
    ON public.website_lock_status(is_locked)
    WHERE is_locked = true;

-- Index for finding locked websites by user
CREATE INDEX IF NOT EXISTS idx_website_lock_status_user_locked
    ON public.website_lock_status(user_id, is_locked);

-- Enable RLS on website_lock_status
ALTER TABLE public.website_lock_status ENABLE ROW LEVEL SECURITY;

-- RLS Policies for website_lock_status
DROP POLICY IF EXISTS "Users can view their own website lock status" ON public.website_lock_status;
CREATE POLICY "Users can view their own website lock status"
    ON public.website_lock_status FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role can manage all website lock status" ON public.website_lock_status;
CREATE POLICY "Service role can manage all website lock status"
    ON public.website_lock_status FOR ALL
    USING (true);

-- Policy for public access to check if a website is locked (for visitors)
DROP POLICY IF EXISTS "Anyone can check website lock status" ON public.website_lock_status;
CREATE POLICY "Anyone can check website lock status"
    ON public.website_lock_status FOR SELECT
    USING (true);

-- Grant permissions
GRANT SELECT ON public.website_lock_status TO authenticated;
GRANT SELECT ON public.website_lock_status TO anon;
GRANT ALL ON public.website_lock_status TO service_role;

-- Add updated_at trigger for website_lock_status
DROP TRIGGER IF EXISTS update_website_lock_status_updated_at ON public.website_lock_status;
CREATE TRIGGER update_website_lock_status_updated_at
    BEFORE UPDATE ON public.website_lock_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE public.website_lock_status IS 'Tracks lock status for individual websites when subscription expires';

-- ==========================================================================
-- SECTION 6: ONE-TIME DATA UPDATE FOR EXISTING USERS
-- ==========================================================================
-- Give all existing users 14 days free before any locking applies.
-- This ensures existing users are not immediately affected by the new system.

DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- Update all existing subscriptions:
    -- 1. Set end_date to NOW() + 14 days (if not already set or if in the past)
    -- 2. Set status to 'active'
    -- 3. Clear any lock-related fields

    UPDATE public.subscriptions
    SET
        end_date = GREATEST(
            COALESCE(end_date, NOW()),
            NOW() + INTERVAL '14 days'
        ),
        status = 'active',
        grace_period_end = NULL,
        lock_reason = NULL,
        locked_at = NULL,
        updated_at = NOW()
    WHERE
        -- Only update if end_date is not set or is in the past or less than 14 days out
        (end_date IS NULL OR end_date < NOW() + INTERVAL '14 days');

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    RAISE NOTICE 'Updated % existing subscription(s) with 14 days free period', updated_count;
END $$;

-- ==========================================================================
-- SECTION 7: HELPER FUNCTIONS FOR SUBSCRIPTION LOCK SYSTEM
-- ==========================================================================

-- Function to check if a user's subscription is locked
CREATE OR REPLACE FUNCTION is_subscription_locked(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_status TEXT;
BEGIN
    SELECT status INTO v_status
    FROM public.subscriptions
    WHERE user_id = p_user_id
    LIMIT 1;

    RETURN COALESCE(v_status = 'locked', false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if a website is locked
CREATE OR REPLACE FUNCTION is_website_locked(p_website_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_locked BOOLEAN;
BEGIN
    SELECT is_locked INTO v_is_locked
    FROM public.website_lock_status
    WHERE website_id = p_website_id
    LIMIT 1;

    RETURN COALESCE(v_is_locked, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get subscription lock info
CREATE OR REPLACE FUNCTION get_subscription_lock_info(p_user_id UUID)
RETURNS TABLE (
    subscription_status TEXT,
    is_locked BOOLEAN,
    locked_at TIMESTAMPTZ,
    lock_reason TEXT,
    grace_period_end TIMESTAMPTZ,
    days_until_lock INTEGER,
    end_date TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.status,
        (s.status = 'locked'),
        s.locked_at,
        s.lock_reason,
        s.grace_period_end,
        CASE
            WHEN s.grace_period_end IS NOT NULL THEN
                GREATEST(0, EXTRACT(DAY FROM (s.grace_period_end - NOW()))::INTEGER)
            WHEN s.end_date IS NOT NULL THEN
                GREATEST(0, EXTRACT(DAY FROM (s.end_date - NOW()))::INTEGER)
            ELSE NULL
        END,
        s.end_date
    FROM public.subscriptions s
    WHERE s.user_id = p_user_id
    LIMIT 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if an email was recently sent (prevent duplicates)
CREATE OR REPLACE FUNCTION was_email_recently_sent(
    p_user_id UUID,
    p_email_type TEXT,
    p_hours_threshold INTEGER DEFAULT 24
)
RETURNS BOOLEAN AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM public.subscription_email_logs
        WHERE user_id = p_user_id
        AND email_type = p_email_type
        AND sent_at > NOW() - (p_hours_threshold || ' hours')::INTERVAL
    ) INTO v_exists;

    RETURN v_exists;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION is_subscription_locked(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_subscription_locked(UUID) TO service_role;

GRANT EXECUTE ON FUNCTION is_website_locked(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_website_locked(UUID) TO anon;
GRANT EXECUTE ON FUNCTION is_website_locked(UUID) TO service_role;

GRANT EXECUTE ON FUNCTION get_subscription_lock_info(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_subscription_lock_info(UUID) TO service_role;

GRANT EXECUTE ON FUNCTION was_email_recently_sent(UUID, TEXT, INTEGER) TO service_role;

-- ==========================================================================
-- SECTION 8: CREATE VIEW FOR SUBSCRIPTION STATUS DASHBOARD
-- ==========================================================================

-- View for easy querying of subscription status with lock info
CREATE OR REPLACE VIEW public.subscription_status_view AS
SELECT
    s.id AS subscription_id,
    s.user_id,
    s.tier,
    s.status,
    s.end_date,
    s.grace_period_end,
    s.locked_at,
    s.lock_reason,
    s.last_payment_reminder,
    s.auto_renew,
    p.email AS user_email,
    CASE
        WHEN s.status = 'locked' THEN 'locked'
        WHEN s.status = 'grace' THEN 'grace_period'
        WHEN s.status = 'expired' THEN 'expired'
        WHEN s.end_date IS NULL THEN 'no_end_date'
        WHEN s.end_date < NOW() THEN 'past_due'
        WHEN s.end_date < NOW() + INTERVAL '5 days' THEN 'expiring_soon'
        ELSE 'active'
    END AS subscription_health,
    CASE
        WHEN s.end_date IS NOT NULL THEN
            GREATEST(0, EXTRACT(DAY FROM (s.end_date - NOW())))::INTEGER
        ELSE NULL
    END AS days_remaining,
    CASE
        WHEN s.grace_period_end IS NOT NULL THEN
            GREATEST(0, EXTRACT(DAY FROM (s.grace_period_end - NOW())))::INTEGER
        ELSE NULL
    END AS grace_days_remaining
FROM public.subscriptions s
LEFT JOIN auth.users p ON s.user_id = p.id;

-- Grant access to the view
GRANT SELECT ON public.subscription_status_view TO service_role;

COMMENT ON VIEW public.subscription_status_view IS 'Dashboard view showing subscription status with lock information';

-- ==========================================================================
-- SUCCESS MESSAGE
-- ==========================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==========================================================================';
    RAISE NOTICE 'BINAAPP SUBSCRIPTION LOCK SYSTEM MIGRATION COMPLETE';
    RAISE NOTICE '==========================================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables modified:';
    RAISE NOTICE '  - subscriptions (added: grace_period_end, lock_reason, last_payment_reminder, locked_at)';
    RAISE NOTICE '';
    RAISE NOTICE 'New tables created:';
    RAISE NOTICE '  - subscription_email_logs (tracks all subscription emails sent)';
    RAISE NOTICE '  - website_lock_status (tracks locked websites)';
    RAISE NOTICE '';
    RAISE NOTICE 'Indexes created:';
    RAISE NOTICE '  - idx_subscriptions_status_end_date';
    RAISE NOTICE '  - idx_subscriptions_status';
    RAISE NOTICE '  - idx_subscriptions_grace_period_end';
    RAISE NOTICE '  - idx_subscriptions_locked_at';
    RAISE NOTICE '  - idx_website_lock_status_website_id';
    RAISE NOTICE '  - idx_website_lock_status_is_locked';
    RAISE NOTICE '  - idx_website_lock_status_user_locked';
    RAISE NOTICE '  - idx_subscription_email_logs_*';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions created:';
    RAISE NOTICE '  - is_subscription_locked(user_id)';
    RAISE NOTICE '  - is_website_locked(website_id)';
    RAISE NOTICE '  - get_subscription_lock_info(user_id)';
    RAISE NOTICE '  - was_email_recently_sent(user_id, email_type, hours)';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - subscription_status_view';
    RAISE NOTICE '';
    RAISE NOTICE 'Data updates:';
    RAISE NOTICE '  - All existing users given 14 days free subscription';
    RAISE NOTICE '';
    RAISE NOTICE 'Status values allowed: active, expired, grace, locked, cancelled, pending';
    RAISE NOTICE '==========================================================================';
END $$;

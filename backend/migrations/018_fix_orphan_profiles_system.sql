-- ============================================================================
-- Migration 018: Fix Orphan Profiles System
-- ============================================================================
-- This migration implements the complete profile auto-creation and
-- orphan prevention system to fix foreign key constraint errors.
--
-- PROBLEM:
--   - websites table has foreign key to profiles table, NOT auth.users
--   - When users register, profile records may not be created (breaks FK)
--   - This causes "foreign key constraint violation" errors on website creation
--
-- SOLUTION:
--   1. Create trigger to auto-create profiles when auth users are created
--   2. Sync existing auth users who don't have profiles
--   3. Create function for safe website counter increment
--
-- RUN THIS IN SUPABASE SQL EDITOR
-- ============================================================================

-- ============================================================================
-- PART 1: AUTO-CREATE PROFILES TRIGGER
-- ============================================================================
-- This trigger automatically creates a profile record whenever a new user
-- registers in Supabase Auth. This ensures the foreign key constraint
-- on the websites table will never fail.

-- Create the trigger function
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    -- Insert a new profile record for the new auth user
    -- Using ON CONFLICT to handle race conditions (if profile already exists)
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

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if it exists (to allow re-running)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create the trigger on auth.users table
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- PART 2: SYNC EXISTING USERS WITHOUT PROFILES
-- ============================================================================
-- This finds all auth users who don't have corresponding profile records
-- and creates them. This is a one-time fix for existing data.

INSERT INTO public.profiles (id, full_name, created_at, updated_at)
SELECT
    u.id,
    COALESCE(
        u.raw_user_meta_data->>'full_name',
        split_part(u.email, '@', 1),
        'User'
    ) as full_name,
    u.created_at,
    NOW() as updated_at
FROM auth.users u
WHERE u.id NOT IN (SELECT id FROM public.profiles)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- PART 3: WEBSITE COUNTER INCREMENT FUNCTION
-- ============================================================================
-- This function safely increments the website count for a user,
-- creating the usage_limits record if it doesn't exist.

CREATE OR REPLACE FUNCTION public.increment_website_count(p_user_id UUID)
RETURNS void AS $$
BEGIN
    -- Try to update existing record
    UPDATE usage_limits
    SET
        websites_count = COALESCE(websites_count, 0) + 1,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- If no rows updated, create new record
    IF NOT FOUND THEN
        INSERT INTO usage_limits (user_id, websites_count, websites_limit, created_at, updated_at)
        VALUES (p_user_id, 1, 1, NOW(), NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            websites_count = COALESCE(usage_limits.websites_count, 0) + 1,
            updated_at = NOW();
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- PART 4: WEBSITE COUNTER DECREMENT FUNCTION
-- ============================================================================
-- This function safely decrements the website count when a website is deleted.

CREATE OR REPLACE FUNCTION public.decrement_website_count(p_user_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE usage_limits
    SET
        websites_count = GREATEST(COALESCE(websites_count, 0) - 1, 0),
        updated_at = NOW()
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- PART 5: VERIFICATION QUERIES
-- ============================================================================
-- Run these queries after migration to verify everything is correct

-- Check for any remaining auth users without profiles (should be 0)
-- SELECT COUNT(*) as missing_profiles
-- FROM auth.users u
-- WHERE u.id NOT IN (SELECT id FROM public.profiles);

-- Check that trigger exists
-- SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';

-- Check total profiles vs auth users (should match)
-- SELECT
--     (SELECT COUNT(*) FROM auth.users) as auth_users,
--     (SELECT COUNT(*) FROM public.profiles) as profiles;

-- ============================================================================
-- NOTES
-- ============================================================================
-- After running this migration:
-- 1. All existing auth users will have profile records
-- 2. All new registrations will automatically get profile records
-- 3. Website creation will no longer fail with FK constraint errors
-- 4. The /api/v1/websites/admin/orphan-check endpoint will report "healthy"
--
-- If you still see issues, run the backend endpoint:
--   POST /api/v1/websites/admin/fix-orphans
-- This will create any missing profiles from the application layer.
-- ============================================================================

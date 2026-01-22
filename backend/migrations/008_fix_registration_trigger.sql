-- ==========================================================================
-- BINAAPP FIX: Registration Trigger Issue
-- ==========================================================================
--
-- PROBLEM: The on_auth_user_created trigger is failing with:
-- "Database error creating new user" (500 error)
--
-- This happens because the trigger tries to insert into 'profiles' and
-- 'subscriptions' tables during auth user creation, and if those tables
-- don't exist or have schema issues, the entire user creation fails.
--
-- SOLUTION: Drop the trigger and let the backend handle profile creation.
-- The backend uses admin.create_user() which bypasses RLS, then manually
-- creates the profile and subscription.
--
-- Run this in Supabase SQL Editor: Dashboard -> SQL Editor -> New Query
-- ==========================================================================

-- Step 1: Drop the problematic trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Step 2: Optionally drop the function (safe to keep for reference)
-- DROP FUNCTION IF EXISTS public.handle_new_user();

-- Step 3: Ensure 'profiles' table exists with correct schema
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT,
    business_name TEXT,
    avatar_url TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 4: Ensure 'subscriptions' table exists
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    tier TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'active',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 5: Enable RLS on both tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- Step 6: Create secure RLS policies for profiles
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON public.profiles;
CREATE POLICY "Users can insert own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Step 7: Create RLS policies for subscriptions
DROP POLICY IF EXISTS "Users can view own subscription" ON public.subscriptions;
CREATE POLICY "Users can view own subscription" ON public.subscriptions
    FOR SELECT USING (auth.uid() = user_id);

-- Step 8: Grant permissions to service_role (for backend admin operations)
GRANT ALL ON public.profiles TO service_role;
GRANT ALL ON public.subscriptions TO service_role;
GRANT ALL ON public.profiles TO authenticated;
GRANT ALL ON public.subscriptions TO authenticated;

-- Step 9: Verify the fix
DO $$
BEGIN
    -- Check if trigger was dropped
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'on_auth_user_created'
    ) THEN
        RAISE NOTICE '✅ Trigger on_auth_user_created has been dropped';
    ELSE
        RAISE WARNING '⚠️ Trigger on_auth_user_created still exists!';
    END IF;

    -- Check if profiles table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'profiles'
    ) THEN
        RAISE NOTICE '✅ profiles table exists';
    ELSE
        RAISE WARNING '⚠️ profiles table does not exist!';
    END IF;

    -- Check if subscriptions table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'subscriptions'
    ) THEN
        RAISE NOTICE '✅ subscriptions table exists';
    ELSE
        RAISE WARNING '⚠️ subscriptions table does not exist!';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Registration fix applied successfully!';
    RAISE NOTICE 'The backend will now handle profile creation.';
    RAISE NOTICE '==============================================';
END $$;

-- ==========================================================================
-- WHAT THIS DOES:
--
-- 1. Removes the trigger that was causing 500 errors during user creation
-- 2. Creates 'profiles' and 'subscriptions' tables if they don't exist
-- 3. Sets up proper RLS policies
-- 4. Grants permissions for the backend service role
--
-- AFTER RUNNING THIS:
-- 1. Redeploy the backend on Render
-- 2. Test registration at https://binaapp.my/register
-- 3. Check backend logs for: "✅ Created auth user:" and "✅ Created user profile:"
-- ==========================================================================

-- BinaApp User Profiles Migration
-- Run this SQL in Supabase SQL Editor
-- This creates the profiles and websites tables with proper RLS policies

-- ============================================
-- 1. CREATE PROFILES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email VARCHAR(255),
    full_name VARCHAR(255),
    business_name VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    profile_image_url TEXT,
    subscription_plan VARCHAR(50) DEFAULT 'free',
    websites_count INTEGER DEFAULT 0,
    max_websites INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 2. CREATE WEBSITES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS websites (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(63) UNIQUE,
    description TEXT,
    template VARCHAR(100),
    html_content TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    published_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 3. ENABLE ROW LEVEL SECURITY
-- ============================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE websites ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 4. PROFILES POLICIES
-- Users can only see/edit their own profile
-- ============================================
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON profiles;
CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON profiles;
CREATE POLICY "Users can insert own profile" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- ============================================
-- 5. WEBSITES POLICIES
-- Users can only manage their own websites
-- ============================================
DROP POLICY IF EXISTS "Users can view own websites" ON websites;
CREATE POLICY "Users can view own websites" ON websites
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create own websites" ON websites;
CREATE POLICY "Users can create own websites" ON websites
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own websites" ON websites;
CREATE POLICY "Users can update own websites" ON websites
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own websites" ON websites;
CREATE POLICY "Users can delete own websites" ON websites
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================
-- 6. AUTO-CREATE PROFILE ON USER SIGNUP
-- ============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger to auto-create profile when user signs up
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- 7. INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX IF NOT EXISTS idx_websites_user_id ON websites(user_id);
CREATE INDEX IF NOT EXISTS idx_websites_subdomain ON websites(subdomain);
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- ============================================
-- 8. GRANT PERMISSIONS (for service role)
-- ============================================
GRANT ALL ON profiles TO service_role;
GRANT ALL ON websites TO service_role;
GRANT ALL ON profiles TO authenticated;
GRANT ALL ON websites TO authenticated;

-- ============================================
-- DONE! Your user profile system is ready.
-- ============================================

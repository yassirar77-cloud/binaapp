-- BinaApp Database Schema for Supabase
-- This file contains all table definitions and relationships

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS TABLE (extends Supabase auth.users)
-- ============================================
-- Note: Supabase handles user authentication
-- We'll use auth.users for authentication
-- Additional user data stored in profiles table

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    full_name TEXT,
    avatar_url TEXT,
    phone TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

-- ============================================
-- SUBSCRIPTIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'active',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscription"
    ON public.subscriptions FOR SELECT
    USING (auth.uid() = user_id);

-- ============================================
-- WEBSITES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.websites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    business_name TEXT NOT NULL,
    business_type TEXT,
    subdomain TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft',
    language TEXT DEFAULT 'ms',

    -- Content
    html_content TEXT,
    meta_title TEXT,
    meta_description TEXT,
    sections TEXT[],
    integrations TEXT[],

    -- Integration settings
    include_whatsapp BOOLEAN DEFAULT false,
    whatsapp_number TEXT,
    include_maps BOOLEAN DEFAULT false,
    location_address TEXT,
    include_ecommerce BOOLEAN DEFAULT false,
    contact_email TEXT,

    -- Publishing
    published_at TIMESTAMP WITH TIME ZONE,
    public_url TEXT,
    preview_url TEXT,

    -- Metadata
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_websites_user_id ON public.websites(user_id);
CREATE INDEX idx_websites_subdomain ON public.websites(subdomain);
CREATE INDEX idx_websites_status ON public.websites(status);

ALTER TABLE public.websites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own websites"
    ON public.websites FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own websites"
    ON public.websites FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own websites"
    ON public.websites FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own websites"
    ON public.websites FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================
-- ANALYTICS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,

    -- Metrics
    total_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    whatsapp_clicks INTEGER DEFAULT 0,
    form_submissions INTEGER DEFAULT 0,
    cart_interactions INTEGER DEFAULT 0,

    -- Timestamps
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(website_id)
);

CREATE INDEX idx_analytics_website_id ON public.analytics(website_id);

ALTER TABLE public.analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view analytics for own websites"
    ON public.analytics FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.websites
            WHERE websites.id = analytics.website_id
            AND websites.user_id = auth.uid()
        )
    );

-- ============================================
-- TEMPLATES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS public.templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    html_template TEXT NOT NULL,
    thumbnail_url TEXT,
    preview_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON public.templates(category);

-- Templates are publicly readable
ALTER TABLE public.templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Templates are viewable by everyone"
    ON public.templates FOR SELECT
    USING (is_active = true);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to increment website views
CREATE OR REPLACE FUNCTION increment_views(website_id UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO public.analytics (website_id, total_views, unique_visitors)
    VALUES (website_id, 1, 1)
    ON CONFLICT (website_id)
    DO UPDATE SET
        total_views = analytics.total_views + 1,
        last_updated = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger for profiles updated_at
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for subscriptions updated_at
CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for websites updated_at
CREATE TRIGGER update_websites_updated_at
    BEFORE UPDATE ON public.websites
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'full_name');

    INSERT INTO public.subscriptions (user_id, tier, status)
    VALUES (NEW.id, 'free', 'active');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert sample templates (optional)
INSERT INTO public.templates (name, category, description, html_template) VALUES
('Restoran Template', 'restaurant', 'Basic restaurant template', '<!DOCTYPE html><html><head><title>Restaurant</title></head><body><h1>My Restaurant</h1></body></html>'),
('Retail Template', 'retail', 'Basic retail template', '<!DOCTYPE html><html><head><title>Store</title></head><body><h1>My Store</h1></body></html>')
ON CONFLICT DO NOTHING;

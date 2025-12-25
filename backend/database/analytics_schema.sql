-- BinaApp Analytics Schema
-- Run this in Supabase SQL Editor

-- Analytics events table
CREATE TABLE IF NOT EXISTS public.analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    event_type TEXT DEFAULT 'pageview',
    visitor_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    device_type TEXT,
    browser TEXT,
    os TEXT,
    country TEXT,
    city TEXT,
    referrer TEXT,
    page_path TEXT DEFAULT '/',
    session_duration INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily stats aggregation table (for faster queries)
CREATE TABLE IF NOT EXISTS public.analytics_daily (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES public.projects(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    mobile_views INTEGER DEFAULT 0,
    desktop_views INTEGER DEFAULT 0,
    avg_session_duration INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, date)
);

-- Add views columns to projects table
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS total_views INTEGER DEFAULT 0;
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS unique_visitors INTEGER DEFAULT 0;

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_analytics_project_id ON public.analytics(project_id);
CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON public.analytics(created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_daily_project_date ON public.analytics_daily(project_id, date);

-- Enable RLS
ALTER TABLE public.analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_daily ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Users can view own project analytics" ON public.analytics;
DROP POLICY IF EXISTS "Users can view own daily analytics" ON public.analytics_daily;
DROP POLICY IF EXISTS "Allow public analytics insert" ON public.analytics;

-- Policies: Users can view analytics for their own projects
CREATE POLICY "Users can view own project analytics"
    ON public.analytics FOR SELECT
    USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

CREATE POLICY "Users can view own daily analytics"
    ON public.analytics_daily FOR SELECT
    USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

-- Allow public insert for tracking (websites are public)
CREATE POLICY "Allow public analytics insert"
    ON public.analytics FOR INSERT
    WITH CHECK (true);

-- Function to increment project views
CREATE OR REPLACE FUNCTION increment_project_views(p_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE public.projects
    SET total_views = COALESCE(total_views, 0) + 1
    WHERE id = p_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

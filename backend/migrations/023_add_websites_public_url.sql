-- Migration 023: Add missing public_url column to websites table
-- Fixes publish error: "Could not find the 'public_url' column of 'websites'"
-- This column stores the public URL after publishing (e.g. https://subdomain.binaapp.my)

ALTER TABLE public.websites ADD COLUMN IF NOT EXISTS public_url TEXT;

-- Also ensure other publish-related columns exist
ALTER TABLE public.websites ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;
ALTER TABLE public.websites ADD COLUMN IF NOT EXISTS preview_url TEXT;

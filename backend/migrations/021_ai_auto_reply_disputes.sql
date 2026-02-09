-- Migration 021: AI Auto-Reply for Disputes
-- Adds ai_auto_reply_disabled column to ai_disputes table
-- This controls whether BinaApp AI automatically replies to customer messages

-- Add ai_auto_reply_disabled column (default false = AI auto-reply is enabled)
ALTER TABLE public.ai_disputes
ADD COLUMN IF NOT EXISTS ai_auto_reply_disabled BOOLEAN DEFAULT false;

-- Add comment for documentation
COMMENT ON COLUMN public.ai_disputes.ai_auto_reply_disabled IS
    'When true, AI auto-reply is disabled for this dispute (e.g. when owner takes over conversation)';

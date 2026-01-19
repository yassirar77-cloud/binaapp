-- Add missing media_url and metadata columns to chat_messages
-- Run this SQL in Supabase SQL Editor

DO $$
BEGIN
    -- Check if table exists first
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
    ) THEN
        RAISE NOTICE 'chat_messages table missing. Run 004_chat_system.sql first.';
        RETURN;
    END IF;

    -- Add media_url column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
        AND column_name = 'media_url'
    ) THEN
        ALTER TABLE public.chat_messages ADD COLUMN media_url TEXT;
        RAISE NOTICE 'Added media_url column to chat_messages';
    ELSE
        RAISE NOTICE 'media_url column already exists in chat_messages';
    END IF;

    -- Add metadata column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
        AND column_name = 'metadata'
    ) THEN
        ALTER TABLE public.chat_messages ADD COLUMN metadata JSONB;
        RAISE NOTICE 'Added metadata column to chat_messages';
    ELSE
        RAISE NOTICE 'metadata column already exists in chat_messages';
    END IF;
END $$;

-- Create indexes for better performance on these columns
CREATE INDEX IF NOT EXISTS idx_chat_messages_media_url ON public.chat_messages(media_url) WHERE media_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chat_messages_metadata ON public.chat_messages USING GIN(metadata) WHERE metadata IS NOT NULL;

-- Verify the columns were added
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
    AND column_name IN ('media_url', 'metadata');

    IF col_count >= 2 THEN
        RAISE NOTICE 'SUCCESS: chat_messages now has media_url and metadata columns';
    ELSE
        RAISE WARNING 'INCOMPLETE: chat_messages still missing some columns';
    END IF;
END $$;

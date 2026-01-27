-- Fix missing message_type column in chat_messages
-- Run this SQL in Supabase SQL Editor

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
    ) THEN
        RAISE NOTICE 'chat_messages table missing. Run 004_chat_system.sql first.';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
        AND column_name = 'message_type'
    ) THEN
        ALTER TABLE public.chat_messages ADD COLUMN message_type TEXT;
        RAISE NOTICE 'Added message_type column to chat_messages';
    ELSE
        RAISE NOTICE 'message_type column already exists in chat_messages';
    END IF;

    ALTER TABLE public.chat_messages ALTER COLUMN message_type SET DEFAULT 'text';
    UPDATE public.chat_messages
    SET message_type = 'text'
    WHERE message_type IS NULL OR message_type = '';
END $$;

CREATE INDEX IF NOT EXISTS idx_chat_messages_type ON public.chat_messages(message_type);

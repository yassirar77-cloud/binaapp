-- Fix missing conversation_id column in chat_messages
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
        AND column_name = 'conversation_id'
    ) THEN
        ALTER TABLE public.chat_messages ADD COLUMN conversation_id UUID;
        RAISE NOTICE 'Added conversation_id column to chat_messages';
    ELSE
        RAISE NOTICE 'conversation_id column already exists in chat_messages';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'chat_conversations'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_schema = 'public'
            AND table_name = 'chat_messages'
            AND constraint_name = 'chat_messages_conversation_id_fkey'
        ) THEN
            BEGIN
                ALTER TABLE public.chat_messages
                    ADD CONSTRAINT chat_messages_conversation_id_fkey
                    FOREIGN KEY (conversation_id)
                    REFERENCES public.chat_conversations(id)
                    ON DELETE CASCADE;
            EXCEPTION
                WHEN others THEN
                    RAISE NOTICE 'Could not add conversation_id foreign key (check existing data/types).';
            END;
        END IF;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id
ON public.chat_messages(conversation_id);

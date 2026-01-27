-- Phone-Based Chat System Migration
-- Adds support for simple phone-based customer identification
-- Run this SQL in Supabase SQL Editor

-- =====================================================
-- 1. FIX CHAT_MESSAGES TABLE
-- =====================================================

-- Add message_text column if it doesn't exist
-- This ensures we have a consistent column name for message content
DO $$
BEGIN
    -- Check if message_text column already exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
        AND column_name = 'message_text'
    ) THEN
        -- Add message_text column
        ALTER TABLE chat_messages ADD COLUMN message_text TEXT;

        -- Migrate data from existing columns
        -- Priority: message > content > empty string
        UPDATE chat_messages
        SET message_text = COALESCE(
            NULLIF(message, ''),
            NULLIF(content, ''),
            ''
        )
        WHERE message_text IS NULL;

        -- Now make it NOT NULL with default
        ALTER TABLE chat_messages ALTER COLUMN message_text SET DEFAULT '';
        ALTER TABLE chat_messages ALTER COLUMN message_text SET NOT NULL;

        RAISE NOTICE 'Added message_text column to chat_messages';
    ELSE
        RAISE NOTICE 'message_text column already exists in chat_messages';
    END IF;
END $$;

-- =====================================================
-- 2. ADD PHONE-BASED INDEXES
-- =====================================================

-- Index for fast lookups by phone number
CREATE INDEX IF NOT EXISTS idx_chat_conversations_phone
ON chat_conversations(customer_phone);

-- Combined index for website + phone lookups
CREATE INDEX IF NOT EXISTS idx_chat_conversations_website_phone
ON chat_conversations(website_id, customer_phone);

-- =====================================================
-- 3. VERIFY COLUMNS EXIST
-- =====================================================

-- Check chat_messages columns
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
    AND column_name IN ('message_text', 'sender_type', 'conversation_id');

    IF col_count >= 3 THEN
        RAISE NOTICE 'SUCCESS: chat_messages has required columns';
    ELSE
        RAISE WARNING 'INCOMPLETE: chat_messages missing some required columns';
    END IF;
END $$;

-- List all columns in chat_messages for verification
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'chat_messages'
ORDER BY ordinal_position;

-- =====================================================
-- 4. GRANT PERMISSIONS (ensure anon can use chat)
-- =====================================================

GRANT SELECT, INSERT, UPDATE ON chat_conversations TO anon;
GRANT SELECT, INSERT, UPDATE ON chat_messages TO anon;
GRANT SELECT, INSERT, UPDATE ON chat_participants TO anon;

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

RAISE NOTICE '✅ Phone-based chat migration completed successfully!';

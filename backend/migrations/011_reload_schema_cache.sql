-- =====================================================
-- RELOAD POSTGREST SCHEMA CACHE
-- =====================================================
-- This migration forces PostgREST to reload its schema cache
-- Fixes PGRST204 errors where columns exist but aren't in cache
--
-- Run this in Supabase SQL Editor when you get schema cache errors
-- =====================================================

-- Force PostgREST to reload schema cache
NOTIFY pgrst, 'reload schema';

-- Verify chat_messages columns exist
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
    AND column_name IN ('id', 'conversation_id', 'sender_type', 'message_text', 'is_read', 'created_at');

    IF col_count >= 6 THEN
        RAISE NOTICE '✅ chat_messages has all required columns';
    ELSE
        RAISE WARNING '⚠️ chat_messages missing some columns (found % of 6)', col_count;
    END IF;
END $$;

-- Verify chat_participants columns exist
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_participants'
    AND column_name IN ('id', 'conversation_id', 'user_type', 'user_id', 'user_name');

    IF col_count >= 5 THEN
        RAISE NOTICE '✅ chat_participants has all required columns';
    ELSE
        RAISE WARNING '⚠️ chat_participants missing some columns (found % of 5)', col_count;
    END IF;
END $$;

-- Verify chat_conversations columns exist
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_conversations'
    AND column_name IN ('id', 'website_id', 'customer_id', 'customer_name', 'customer_phone', 'status');

    IF col_count >= 6 THEN
        RAISE NOTICE '✅ chat_conversations has all required columns';
    ELSE
        RAISE WARNING '⚠️ chat_conversations missing some columns (found % of 6)', col_count;
    END IF;
END $$;

-- List all columns in chat_messages
SELECT
    'chat_messages' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'chat_messages'
ORDER BY ordinal_position;

-- List all columns in chat_participants
SELECT
    'chat_participants' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'chat_participants'
ORDER BY ordinal_position;

-- List all columns in chat_conversations
SELECT
    'chat_conversations' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'chat_conversations'
ORDER BY ordinal_position;

RAISE NOTICE '✅ Schema cache reload complete. Check column lists above.';

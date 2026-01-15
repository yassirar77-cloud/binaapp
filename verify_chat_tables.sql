-- ==========================================================================
-- BINAAPP CHAT TABLES VERIFICATION SCRIPT
-- ==========================================================================
-- Run this in Supabase SQL Editor to check if chat tables exist
-- If tables don't exist, run backend/migrations/004_chat_system.sql
-- ==========================================================================

-- Check if chat tables exist
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_schema = 'public'
     AND table_name = t.table_name) as column_count,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename = t.table_name
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as status
FROM (
    VALUES
        ('chat_conversations'),
        ('chat_messages'),
        ('chat_participants')
) AS t(table_name)
ORDER BY table_name;

-- Check if RLS is enabled
SELECT
    schemaname,
    tablename,
    CASE
        WHEN rowsecurity THEN '✅ ENABLED'
        ELSE '❌ DISABLED'
    END as rls_status
FROM pg_tables
WHERE schemaname = 'public'
AND tablename LIKE 'chat_%'
ORDER BY tablename;

-- Check indexes
SELECT
    schemaname,
    tablename,
    indexname,
    '✅ EXISTS' as status
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename LIKE 'chat_%'
ORDER BY tablename, indexname;

-- Check RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    '✅ EXISTS' as status
FROM pg_policies
WHERE schemaname = 'public'
AND tablename LIKE 'chat_%'
ORDER BY tablename, policyname;

-- Check foreign keys
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    '✅ EXISTS' as status
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
AND tc.table_name LIKE 'chat_%'
ORDER BY tc.table_name, kcu.column_name;

-- Summary report
SELECT
    'SUMMARY' as report_type,
    (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'chat_%') as tables_count,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND tablename LIKE 'chat_%') as indexes_count,
    (SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public' AND tablename LIKE 'chat_%') as policies_count,
    CASE
        WHEN (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'chat_%') = 3
        THEN '✅ ALL CHAT TABLES EXIST'
        ELSE '❌ MISSING CHAT TABLES - RUN 004_chat_system.sql'
    END as overall_status;

-- ==========================================================================
-- EXPECTED RESULTS:
-- ==========================================================================
-- Tables: 3 (chat_conversations, chat_messages, chat_participants)
-- Indexes: 9 total
-- Policies: 12+ total
-- RLS: Enabled on all 3 tables
-- ==========================================================================

-- If you see "❌ MISSING CHAT TABLES", run this command:
-- Copy and paste the contents of backend/migrations/004_chat_system.sql
-- into the Supabase SQL Editor and click RUN
-- ==========================================================================

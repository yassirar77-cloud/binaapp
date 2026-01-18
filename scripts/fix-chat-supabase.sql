-- ============================================
-- BINAAPP CHAT SYSTEM - SUPABASE FIX SCRIPT
-- ============================================
-- Run this script in your Supabase SQL Editor to fix chat system

-- STEP 1: Verify table structure
-- ============================================
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'chat_messages'
ORDER BY ordinal_position;

-- STEP 2: Verify trigger exists
-- ============================================
SELECT
    tgname as trigger_name,
    tgenabled as is_enabled
FROM pg_trigger
WHERE tgrelid = 'chat_messages'::regclass;

-- STEP 3: Recreate sync trigger (ensures all 3 columns stay in sync)
-- ============================================
DROP TRIGGER IF EXISTS sync_messages_trigger ON chat_messages;

CREATE OR REPLACE FUNCTION sync_message_columns()
RETURNS TRIGGER AS $$
BEGIN
  -- When inserting or updating, sync all three columns
  -- Priority: message_text > message > content
  IF NEW.message_text IS NOT NULL AND NEW.message_text != '' THEN
    NEW.message := NEW.message_text;
    NEW.content := NEW.message_text;
  ELSIF NEW.message IS NOT NULL AND NEW.message != '' THEN
    NEW.message_text := NEW.message;
    NEW.content := NEW.message;
  ELSIF NEW.content IS NOT NULL AND NEW.content != '' THEN
    NEW.message_text := NEW.content;
    NEW.message := NEW.content;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_messages_trigger
BEFORE INSERT OR UPDATE ON chat_messages
FOR EACH ROW
EXECUTE FUNCTION sync_message_columns();

-- STEP 4: Fix existing messages (backfill missing columns)
-- ============================================
UPDATE chat_messages
SET
    message_text = COALESCE(message_text, message, content, ''),
    message = COALESCE(message, message_text, content, ''),
    content = COALESCE(content, message_text, message, '')
WHERE
    message_text IS NULL
    OR message IS NULL
    OR content IS NULL
    OR message_text = ''
    OR message = ''
    OR content = '';

-- STEP 5: Enable Row Level Security
-- ============================================
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;

-- STEP 6: Create permissive RLS policies (allow all access for now)
-- ============================================
-- Drop existing policies
DROP POLICY IF EXISTS "chat_messages_all" ON chat_messages;
DROP POLICY IF EXISTS "chat_conversations_all" ON chat_conversations;

-- Allow ALL operations on chat_messages
CREATE POLICY "chat_messages_all"
ON chat_messages
FOR ALL
USING (true)
WITH CHECK (true);

-- Allow ALL operations on chat_conversations
CREATE POLICY "chat_conversations_all"
ON chat_conversations
FOR ALL
USING (true)
WITH CHECK (true);

-- STEP 7: Enable Realtime for chat tables
-- ============================================
-- Remove from publication if exists
ALTER PUBLICATION supabase_realtime DROP TABLE IF EXISTS chat_messages;
ALTER PUBLICATION supabase_realtime DROP TABLE IF EXISTS chat_conversations;

-- Add to publication
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_conversations;

-- STEP 8: Verify setup
-- ============================================
-- Check if realtime is enabled
SELECT schemaname, tablename
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime'
AND tablename IN ('chat_messages', 'chat_conversations');

-- Check RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies
WHERE tablename IN ('chat_messages', 'chat_conversations')
ORDER BY tablename, policyname;

-- Count messages to verify data
SELECT
    COUNT(*) as total_messages,
    COUNT(message_text) as with_message_text,
    COUNT(message) as with_message,
    COUNT(content) as with_content
FROM chat_messages;

-- Show recent messages (verify columns are populated)
SELECT
    id,
    conversation_id,
    sender_type,
    message_text,
    message,
    content,
    created_at
FROM chat_messages
ORDER BY created_at DESC
LIMIT 10;

-- ============================================
-- VERIFICATION COMPLETE
-- ============================================
-- If you see:
-- ✅ Trigger: sync_messages_trigger exists and is enabled
-- ✅ All messages have message_text, message, and content populated
-- ✅ RLS policies allow access
-- ✅ Realtime is enabled for both tables
--
-- Then your chat system should be working!
-- ============================================

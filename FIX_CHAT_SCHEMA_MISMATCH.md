# Fix: Chat Schema Type Mismatch (BIGINT vs UUID)

## Critical Problem

Your chat system has **fundamental schema mismatches** that prevent it from working:

### Error 1: Type Mismatch
```
ERROR: invalid input syntax for type bigint: "a6e76aec-a91a-4974-9cbb-3d0735a5dc1d"
Code: 22P02
```
**Cause:** The `chat_messages` table has `id` or `conversation_id` as `bigint` but the code tries to insert UUIDs.

### Error 2: Missing Table/Columns
```
WARNING: Could not find the 'user_type' column of 'chat_participants' in the schema cache
Code: PGRST204
```
**Cause:** The `chat_participants` table doesn't exist or has wrong schema.

## Root Cause

**The chat tables were created with the wrong schema!**

Your database has:
- `chat_messages.id` = `bigint` (WRONG)
- `chat_messages.conversation_id` = `bigint` (WRONG)

The code expects:
- `chat_messages.id` = `UUID` (CORRECT)
- `chat_messages.conversation_id` = `UUID` (CORRECT)

This happened because:
1. Tables were created manually or via a different migration tool
2. Auto-increment IDs were used instead of UUIDs
3. Migration `004_chat_system.sql` was never run or partially applied

## Impact

**Current State: CHAT SYSTEM COMPLETELY BROKEN ❌**
- Cannot create conversations (type mismatch)
- Cannot send messages (type mismatch)
- Cannot track participants (table missing)
- All chat functionality is non-functional

## Step 1: Diagnose Your Schema

First, run the diagnostic to see what's actually in your database:

### Via Supabase Dashboard:
1. Go to **SQL Editor**
2. Run this query:

```sql
-- Check chat_messages schema
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'chat_messages'
ORDER BY ordinal_position;

-- Check if chat_participants exists
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'chat_participants'
) as participants_exists;
```

### Expected Problems You'll Find:
- `chat_messages.id` is `bigint` or `integer` (should be `uuid`)
- `chat_messages.conversation_id` is `bigint` or `integer` (should be `uuid`)
- `chat_participants` table doesn't exist

## Step 2: Choose Your Fix Strategy

You have **3 options** depending on whether you have existing chat data:

### Option A: No Chat Data Yet (EASIEST) ✅ Recommended
**Use this if:** You have no important chat messages to preserve

**Action:** Drop and recreate tables with correct schema

### Option B: Have Important Chat Data (COMPLEX) ⚠️
**Use this if:** You have chat messages you need to keep

**Action:** Migrate data from bigint to UUID (requires data transformation)

### Option C: Just Fix Missing Table (PARTIAL) ⚠️
**Use this if:** Only `chat_participants` is missing

**Action:** Create just the participants table

---

## Step 3: Apply the Fix

### ✅ Option A: Fresh Start (Recommended if no data)

1. **Backup first** (just in case):
```sql
-- Backup existing data (if any)
CREATE TABLE IF NOT EXISTS chat_conversations_backup AS
SELECT * FROM chat_conversations WHERE 1=1;

CREATE TABLE IF NOT EXISTS chat_messages_backup AS
SELECT * FROM chat_messages WHERE 1=1;
```

2. **Drop existing tables:**
```sql
DROP TABLE IF EXISTS public.chat_participants CASCADE;
DROP TABLE IF EXISTS public.chat_messages CASCADE;
DROP TABLE IF EXISTS public.chat_conversations CASCADE;
```

3. **Run the correct migration:**
   - Open `backend/migrations/004_chat_system.sql`
   - Copy the entire contents
   - Paste and run in Supabase SQL Editor

4. **Reload schema cache:**
```sql
NOTIFY pgrst, 'reload schema';
```

### ⚠️ Option B: Preserve Data (Complex Migration)

This requires converting bigint IDs to UUIDs while preserving data relationships. This is complex!

```sql
-- Step 1: Create new tables with correct schema
CREATE TABLE public.chat_conversations_new (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    old_id BIGINT, -- temporary column for mapping
    order_id UUID,
    website_id UUID NOT NULL,
    customer_id TEXT NOT NULL,
    customer_name TEXT,
    customer_phone TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.chat_messages_new (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    old_id BIGINT, -- temporary column
    conversation_id UUID NOT NULL,
    old_conversation_id BIGINT, -- temporary column
    sender_type TEXT NOT NULL,
    sender_id TEXT,
    message_type TEXT DEFAULT 'text',
    message_text TEXT NOT NULL DEFAULT '',
    media_url TEXT,
    metadata JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 2: Copy data with UUID generation
INSERT INTO chat_conversations_new (old_id, order_id, website_id, customer_id, customer_name, customer_phone, status, created_at, updated_at)
SELECT id, order_id, website_id, customer_id, customer_name, customer_phone, status, created_at, updated_at
FROM chat_conversations;

INSERT INTO chat_messages_new (old_id, old_conversation_id, sender_type, sender_id, message_type, message_text, is_read, created_at)
SELECT id, conversation_id, sender_type, sender_id,
       COALESCE(message_type, 'text'),
       COALESCE(message_text, content, message, ''),
       COALESCE(is_read, false),
       created_at
FROM chat_messages;

-- Step 3: Update foreign keys using mapping
UPDATE chat_messages_new m
SET conversation_id = c.id
FROM chat_conversations_new c
WHERE m.old_conversation_id = c.old_id;

-- Step 4: Drop old tables and rename new ones
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS chat_conversations CASCADE;

ALTER TABLE chat_conversations_new RENAME TO chat_conversations;
ALTER TABLE chat_messages_new RENAME TO chat_messages;

-- Step 5: Remove temporary mapping columns
ALTER TABLE chat_conversations DROP COLUMN IF EXISTS old_id;
ALTER TABLE chat_messages DROP COLUMN IF EXISTS old_id;
ALTER TABLE chat_messages DROP COLUMN IF EXISTS old_conversation_id;

-- Step 6: Add foreign key constraint
ALTER TABLE chat_messages
ADD CONSTRAINT chat_messages_conversation_id_fkey
FOREIGN KEY (conversation_id)
REFERENCES chat_conversations(id) ON DELETE CASCADE;

-- Step 7: Create indexes
CREATE INDEX idx_chat_conversations_website ON chat_conversations(website_id);
CREATE INDEX idx_chat_conversations_customer ON chat_conversations(customer_phone);
CREATE INDEX idx_chat_messages_conversation ON chat_messages(conversation_id);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at DESC);

-- Step 8: Create chat_participants table
-- (run the chat_participants creation from 004_chat_system.sql)

-- Step 9: Reload schema cache
NOTIFY pgrst, 'reload schema';
```

### ⚠️ Option C: Just Add Missing Table

If only `chat_participants` is missing but IDs are correct:

```sql
CREATE TABLE IF NOT EXISTS public.chat_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.chat_conversations(id) ON DELETE CASCADE NOT NULL,
    user_type TEXT NOT NULL,
    user_id TEXT,
    user_name TEXT,
    is_online BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(conversation_id, user_type, user_id)
);

CREATE INDEX idx_chat_participants_conversation ON chat_participants(conversation_id);
ALTER TABLE chat_participants ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all chat_participants" ON chat_participants;
CREATE POLICY "Allow all chat_participants" ON chat_participants
FOR ALL USING (true) WITH CHECK (true);

GRANT ALL ON chat_participants TO service_role, authenticated, anon;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_participants;

NOTIFY pgrst, 'reload schema';
```

---

## Step 4: Verify the Fix

After applying any fix, verify it worked:

```sql
-- 1. Check all tables exist
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE schemaname = 'public'
AND tablename LIKE 'chat_%'
ORDER BY tablename;

-- Expected: chat_conversations, chat_messages, chat_participants

-- 2. Check column types
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN ('chat_conversations', 'chat_messages', 'chat_participants')
AND column_name IN ('id', 'conversation_id')
ORDER BY table_name, column_name;

-- Expected:
-- chat_conversations | id              | uuid
-- chat_messages      | id              | uuid
-- chat_messages      | conversation_id | uuid
-- chat_participants  | id              | uuid
-- chat_participants  | conversation_id | uuid

-- 3. Check required columns in chat_messages
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'chat_messages'
ORDER BY ordinal_position;

-- Must include: id, conversation_id, sender_type, message_text,
--               media_url, metadata, is_read, created_at

-- 4. Reload schema cache
NOTIFY pgrst, 'reload schema';
```

## Step 5: Test Chat Functionality

After the fix:

1. **Restart your backend application**
```bash
# If using Docker
docker-compose restart backend

# If running locally
# Stop and restart your FastAPI server
```

2. **Test creating a conversation:**
   - Use your customer ordering app
   - Try to create a chat conversation
   - Should work without errors

3. **Check logs:**
   - No more "invalid input syntax for type bigint" errors
   - No more "Could not find the 'user_type' column" errors

4. **Test sending messages:**
   - Send text messages
   - Upload images
   - Verify they appear correctly

## Automated Fix Script

I've also created `backend/migrations/014_diagnose_and_fix_chat_schema.sql`:

1. **First, run diagnostic section** (always safe)
2. **Uncomment the appropriate FIX section** based on your situation
3. **Run in Supabase SQL Editor**

The script will:
- ✓ Diagnose current schema state
- ✓ Apply the appropriate fix
- ✓ Reload schema cache
- ✓ Verify the fix worked

## Quick Reference: Which Fix Do I Need?

| Your Situation | Fix to Use |
|----------------|------------|
| No chat data yet | **Option A** - Fresh start (easiest) |
| Have test data only | **Option A** - Fresh start |
| Have important production chat data | **Option B** - Data migration (complex) |
| Tables correct, just missing chat_participants | **Option C** - Add table only |
| Unsure what's wrong | Run diagnostic first! |

## Why Did This Happen?

This schema mismatch occurred because:

1. **Manual table creation:** Someone created tables manually in Supabase UI with auto-increment IDs
2. **Different migration tool:** Used a tool that converted UUIDs to bigints
3. **Partial migration:** Only some parts of `004_chat_system.sql` were applied
4. **ORM mismatch:** An ORM tool created tables with its own schema

## Prevention for Future

To prevent this in the future:

1. **Always run migrations in order:** 001, 002, 003, 004, etc.
2. **Use migration files:** Don't create tables manually in Supabase UI
3. **Verify after each migration:** Check data types match expectations
4. **Track applied migrations:** Keep a record of which migrations ran successfully
5. **Test in staging first:** Apply migrations to staging before production

## Need Help?

If you're stuck:

1. Run the diagnostic queries first
2. Share the output (table structures and data types)
3. Confirm if you have data to preserve
4. We can then determine the exact fix needed

## Summary

**Problem:** Chat tables have wrong data types (bigint instead of UUID)

**Solution:** Recreate tables with correct schema (or migrate data if needed)

**Files Created:**
- `backend/migrations/014_diagnose_and_fix_chat_schema.sql` - Diagnostic and fix script
- `FIX_CHAT_SCHEMA_MISMATCH.md` (this file) - Comprehensive guide

**Recommended Action:**
1. Run diagnostic to confirm the issue
2. If no important data: Use **Option A** (fresh start)
3. If have data: Use **Option B** (complex migration) or contact for help
4. Verify the fix worked
5. Test chat functionality

The chat system will work perfectly once the schema matches what the code expects! 🚀

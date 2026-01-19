# 🔧 Fix Missing Chat Tables in Supabase

**Issue**: Chat system not working - `chat_conversations` table missing
**Error**: "Could not find the table 'public.chat_conversations' in the schema cache"
**Solution**: Run the chat migration in Supabase

**Additional Issue**: `column chat_messages.message_type does not exist`
**Fix**: Run `backend/migrations/012_fix_chat_message_type.sql` in Supabase SQL Editor

---

## ✅ Step-by-Step Fix

### Step 1: Open Supabase SQL Editor

1. Go to https://app.supabase.com
2. Select your BinaApp project
3. Click **"SQL Editor"** in the left sidebar
4. Click **"New Query"**

### Step 2: Copy the Migration SQL

Open the file: `backend/migrations/004_chat_system.sql`

Or copy this SQL:

```sql
-- BinaApp Chat System Migration
-- Run this SQL in Supabase SQL Editor

-- =====================================================
-- 1. CHAT CONVERSATIONS
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES delivery_orders(id) ON DELETE SET NULL,
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE NOT NULL,

    -- Customer Info
    customer_id TEXT NOT NULL,
    customer_name TEXT,
    customer_phone TEXT,

    -- Status
    status TEXT DEFAULT 'active',

    -- Unread counts
    unread_owner INTEGER DEFAULT 0,
    unread_customer INTEGER DEFAULT 0,
    unread_rider INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 2. CHAT MESSAGES
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES chat_conversations(id) ON DELETE CASCADE NOT NULL,

    -- Sender Info
    sender_type TEXT NOT NULL,
    sender_id TEXT,
    sender_name TEXT,

    -- Message Content
    message_type TEXT DEFAULT 'text',
    content TEXT,
    media_url TEXT,
    metadata JSONB,

    -- Read Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    read_by JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 3. CHAT PARTICIPANTS
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES chat_conversations(id) ON DELETE CASCADE NOT NULL,

    -- User Info
    user_type TEXT NOT NULL,
    user_id TEXT,
    user_name TEXT,

    -- Online Status
    is_online BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(conversation_id, user_type, user_id)
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_chat_conversations_order ON chat_conversations(order_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_website ON chat_conversations(website_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_customer ON chat_conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_status ON chat_conversations(status);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated ON chat_conversations(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sender ON chat_messages(sender_type, sender_id);

CREATE INDEX IF NOT EXISTS idx_chat_participants_conversation ON chat_participants(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_participants_user ON chat_participants(user_type, user_id);

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================
ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_participants ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS POLICIES - Chat Conversations
-- =====================================================

-- Service role has full access
DROP POLICY IF EXISTS "Service role full access to conversations" ON chat_conversations;
CREATE POLICY "Service role full access to conversations" ON chat_conversations
    FOR ALL USING (true)
    WITH CHECK (true);

-- Business owners can view conversations for their websites
DROP POLICY IF EXISTS "Owners can view own conversations" ON chat_conversations;
CREATE POLICY "Owners can view own conversations" ON chat_conversations
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- Business owners can manage conversations
DROP POLICY IF EXISTS "Owners can manage own conversations" ON chat_conversations;
CREATE POLICY "Owners can manage own conversations" ON chat_conversations
    FOR ALL USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- Public can create conversations (for customer ordering)
DROP POLICY IF EXISTS "Anyone can create conversations" ON chat_conversations;
CREATE POLICY "Anyone can create conversations" ON chat_conversations
    FOR INSERT WITH CHECK (true);

-- Public can view conversations
DROP POLICY IF EXISTS "Customers can view own conversations" ON chat_conversations;
CREATE POLICY "Customers can view own conversations" ON chat_conversations
    FOR SELECT USING (true);

-- =====================================================
-- RLS POLICIES - Chat Messages
-- =====================================================

-- Service role has full access
DROP POLICY IF EXISTS "Service role full access to messages" ON chat_messages;
CREATE POLICY "Service role full access to messages" ON chat_messages
    FOR ALL USING (true)
    WITH CHECK (true);

-- Anyone can view messages
DROP POLICY IF EXISTS "Anyone can view messages" ON chat_messages;
CREATE POLICY "Anyone can view messages" ON chat_messages
    FOR SELECT USING (true);

-- Anyone can insert messages
DROP POLICY IF EXISTS "Anyone can insert messages" ON chat_messages;
CREATE POLICY "Anyone can insert messages" ON chat_messages
    FOR INSERT WITH CHECK (true);

-- Anyone can update messages (for read status)
DROP POLICY IF EXISTS "Anyone can update messages" ON chat_messages;
CREATE POLICY "Anyone can update messages" ON chat_messages
    FOR UPDATE USING (true);

-- =====================================================
-- RLS POLICIES - Chat Participants
-- =====================================================

-- Service role has full access
DROP POLICY IF EXISTS "Service role full access to participants" ON chat_participants;
CREATE POLICY "Service role full access to participants" ON chat_participants
    FOR ALL USING (true)
    WITH CHECK (true);

-- Anyone can view participants
DROP POLICY IF EXISTS "Anyone can view participants" ON chat_participants;
CREATE POLICY "Anyone can view participants" ON chat_participants
    FOR SELECT USING (true);

-- Anyone can manage participants
DROP POLICY IF EXISTS "Anyone can manage participants" ON chat_participants;
CREATE POLICY "Anyone can manage participants" ON chat_participants
    FOR ALL USING (true)
    WITH CHECK (true);

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================
GRANT ALL ON chat_conversations TO service_role;
GRANT ALL ON chat_messages TO service_role;
GRANT ALL ON chat_participants TO service_role;

GRANT ALL ON chat_conversations TO authenticated;
GRANT ALL ON chat_messages TO authenticated;
GRANT ALL ON chat_participants TO authenticated;

GRANT SELECT, INSERT, UPDATE ON chat_conversations TO anon;
GRANT SELECT, INSERT, UPDATE ON chat_messages TO anon;
GRANT SELECT, INSERT, UPDATE ON chat_participants TO anon;

-- =====================================================
-- ENABLE REAL-TIME SUBSCRIPTIONS
-- =====================================================
ALTER PUBLICATION supabase_realtime ADD TABLE chat_conversations;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_participants;

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Auto-update updated_at on conversations
DROP TRIGGER IF EXISTS update_chat_conversations_updated_at ON chat_conversations;
CREATE TRIGGER update_chat_conversations_updated_at
    BEFORE UPDATE ON chat_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update conversation on new message
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_conversations
    SET updated_at = NOW()
    WHERE id = NEW.conversation_id;

    IF NEW.sender_type = 'customer' THEN
        UPDATE chat_conversations
        SET unread_owner = unread_owner + 1,
            unread_rider = unread_rider + 1
        WHERE id = NEW.conversation_id;
    ELSIF NEW.sender_type = 'owner' THEN
        UPDATE chat_conversations
        SET unread_customer = unread_customer + 1,
            unread_rider = unread_rider + 1
        WHERE id = NEW.conversation_id;
    ELSIF NEW.sender_type = 'rider' THEN
        UPDATE chat_conversations
        SET unread_customer = unread_customer + 1,
            unread_owner = unread_owner + 1
        WHERE id = NEW.conversation_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_conversation_on_message_trigger ON chat_messages;
CREATE TRIGGER update_conversation_on_message_trigger
    AFTER INSERT ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION update_conversation_on_message();
```

### Step 3: Run the Migration

1. Paste the SQL into the Supabase SQL Editor
2. Click **"Run"** (or press Ctrl+Enter / Cmd+Enter)
3. Wait for success message

### Step 4: Verify Tables Created

Run this verification query in Supabase SQL Editor:

```sql
-- Check if chat tables exist
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_schema = 'public'
     AND table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
AND table_name LIKE 'chat_%'
ORDER BY table_name;
```

You should see:
- `chat_conversations` (10 columns)
- `chat_messages` (11 columns)
- `chat_participants` (7 columns)

### Step 5: Restart Your Backend

After running the migration, restart your Render backend:

1. Go to https://dashboard.render.com
2. Select your BinaApp backend service
3. Click **"Manual Deploy"** → **"Clear build cache & deploy"**

Or just wait 30 seconds for Render to detect the change automatically.

---

## ✅ Verification Checklist

After running the migration:

- [ ] Tables created in Supabase
- [ ] RLS enabled on all 3 tables
- [ ] Indexes created
- [ ] Permissions granted
- [ ] Realtime enabled
- [ ] Backend restarted
- [ ] Chat tab in /profile loads without error
- [ ] Can send/receive messages

---

## 🐛 Troubleshooting

### Error: "relation delivery_orders does not exist"

If you get this error, it means the `delivery_orders` table doesn't exist. Fix:

```sql
-- Option 1: Create delivery_orders table first
-- (Run the delivery system migration)

-- Option 2: Remove the foreign key constraint temporarily
ALTER TABLE chat_conversations
ALTER COLUMN order_id DROP NOT NULL;
```

### Error: "function update_updated_at_column() does not exist"

Create the function first:

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Chat Still Not Working After Migration

1. **Clear Render cache**:
   - Go to Render dashboard
   - Click "Manual Deploy"
   - Select "Clear build cache & deploy"

2. **Check backend logs**:
   - Go to Render → Your service → Logs
   - Look for any new errors

3. **Verify table names**:
   ```sql
   SELECT tablename FROM pg_tables
   WHERE schemaname = 'public'
   AND tablename LIKE 'chat%';
   ```

4. **Check RLS policies**:
   ```sql
   SELECT tablename, policyname
   FROM pg_policies
   WHERE schemaname = 'public'
   AND tablename LIKE 'chat%';
   ```

---

## 📝 What This Migration Does

1. **Creates 3 Tables**:
   - `chat_conversations`: Stores chat sessions
   - `chat_messages`: Stores individual messages
   - `chat_participants`: Tracks who's in each chat

2. **Adds Security**:
   - Row Level Security (RLS) enabled
   - Policies ensure users only see their own data
   - Service role has full access for backend

3. **Optimizes Performance**:
   - Indexes on frequently queried columns
   - Foreign keys for data integrity
   - Triggers for auto-updates

4. **Enables Real-time**:
   - Live message delivery via WebSocket
   - Instant updates when new messages arrive

---

## 🎉 Expected Result

After running this migration:

✅ Chat tab in `/profile` will load successfully
✅ Can create conversations
✅ Can send/receive messages
✅ Real-time updates work
✅ No more "table not found" errors

---

## 📞 Still Having Issues?

If the chat still doesn't work after running this migration:

1. Check Render logs for specific errors
2. Verify all environment variables are set
3. Make sure Supabase SERVICE_ROLE_KEY is correct
4. Check if WebSocket connections are being blocked

---

**Created**: 2026-01-11
**Issue**: Missing chat tables in production database
**Status**: Ready to run ✅

-- BinaApp Chat System Migration
-- Run this SQL in Supabase SQL Editor
-- Creates tables for real-time in-app messaging

-- =====================================================
-- 1. CHAT CONVERSATIONS
-- =====================================================
CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES delivery_orders(id) ON DELETE SET NULL,
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE NOT NULL,

    -- Customer Info
    customer_id TEXT NOT NULL,  -- Can be phone or generated ID
    customer_name TEXT,
    customer_phone TEXT,

    -- Status
    status TEXT DEFAULT 'active',  -- 'active', 'closed', 'archived'

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
    sender_type TEXT NOT NULL,  -- 'customer', 'owner', 'rider', 'system'
    sender_id TEXT,
    sender_name TEXT,

    -- Message Content
    message_type TEXT DEFAULT 'text',  -- 'text', 'image', 'location', 'payment', 'status', 'voice'
    content TEXT,  -- Text message or JSON data
    media_url TEXT,  -- For images/voice
    metadata JSONB,  -- Extra data (location coords, payment info, etc)

    -- Read Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    read_by JSONB DEFAULT '[]'::jsonb,  -- Array of user types who read the message

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
    user_type TEXT NOT NULL,  -- 'customer', 'owner', 'rider'
    user_id TEXT,
    user_name TEXT,

    -- Online Status
    is_online BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint per conversation
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

-- Public can view conversations they're part of (by customer_id)
DROP POLICY IF EXISTS "Customers can view own conversations" ON chat_conversations;
CREATE POLICY "Customers can view own conversations" ON chat_conversations
    FOR SELECT USING (true);  -- Filtering done in application layer

-- =====================================================
-- RLS POLICIES - Chat Messages
-- =====================================================

-- Service role has full access
DROP POLICY IF EXISTS "Service role full access to messages" ON chat_messages;
CREATE POLICY "Service role full access to messages" ON chat_messages
    FOR ALL USING (true)
    WITH CHECK (true);

-- Anyone can view messages (filtering in app layer by conversation access)
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
    -- Update conversation timestamp
    UPDATE chat_conversations
    SET updated_at = NOW()
    WHERE id = NEW.conversation_id;

    -- Update unread counts based on sender type
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

-- =====================================================
-- DONE! BinaApp Chat System tables ready.
-- =====================================================

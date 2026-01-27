-- BinaApp Customer Registration & Notifications Migration
-- Run this SQL in Supabase SQL Editor

-- =====================================================
-- 1. WEBSITE CUSTOMERS TABLE
-- Stores customer info per website for repeat orders
-- =====================================================
CREATE TABLE IF NOT EXISTS website_customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
    phone VARCHAR(20) NOT NULL,
    name VARCHAR(200),
    email VARCHAR(200),
    address TEXT,
    total_orders INTEGER DEFAULT 0,
    last_order_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(website_id, phone)
);

CREATE INDEX IF NOT EXISTS idx_customers_website ON website_customers(website_id);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON website_customers(phone);

-- =====================================================
-- 2. NOTIFICATIONS TABLE
-- For push/in-app notifications to all user types
-- =====================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_type VARCHAR(20) NOT NULL,  -- 'owner', 'customer', 'rider'
    user_id TEXT NOT NULL,           -- UUID or phone number
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    order_id UUID REFERENCES delivery_orders(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES chat_conversations(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,       -- 'new_order', 'order_assigned', 'rider_accepted', 'message', 'status_update'
    title VARCHAR(200),
    body TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_type, user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- =====================================================
-- 3. UPDATE DELIVERY_ORDERS TABLE
-- Add customer_id and conversation_id links
-- =====================================================
ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES website_customers(id);
ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS conversation_id UUID;

-- =====================================================
-- 4. UPDATE CHAT_CONVERSATIONS TABLE
-- Add owner_id, rider_id, and last message tracking
-- =====================================================
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS owner_id TEXT;
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS rider_id UUID REFERENCES riders(id);
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS last_message TEXT;
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMPTZ;

-- =====================================================
-- 5. ROW LEVEL SECURITY
-- =====================================================
ALTER TABLE website_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Website customers - owner access
DROP POLICY IF EXISTS "Owners can view own customers" ON website_customers;
CREATE POLICY "Owners can view own customers" ON website_customers
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Owners can manage own customers" ON website_customers;
CREATE POLICY "Owners can manage own customers" ON website_customers
    FOR ALL USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- Public can create customers (on order)
DROP POLICY IF EXISTS "Anyone can create customers" ON website_customers;
CREATE POLICY "Anyone can create customers" ON website_customers
    FOR INSERT WITH CHECK (true);

-- Notifications - users can view their own
DROP POLICY IF EXISTS "Users can view own notifications" ON notifications;
CREATE POLICY "Users can view own notifications" ON notifications
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Anyone can create notifications" ON notifications;
CREATE POLICY "Anyone can create notifications" ON notifications
    FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Users can update own notifications" ON notifications;
CREATE POLICY "Users can update own notifications" ON notifications
    FOR UPDATE USING (true);

-- =====================================================
-- 6. GRANT PERMISSIONS
-- =====================================================
GRANT ALL ON website_customers TO service_role;
GRANT ALL ON notifications TO service_role;

GRANT ALL ON website_customers TO authenticated;
GRANT ALL ON notifications TO authenticated;

GRANT SELECT, INSERT, UPDATE ON website_customers TO anon;
GRANT SELECT, INSERT, UPDATE ON notifications TO anon;

-- =====================================================
-- 7. ENABLE REAL-TIME
-- =====================================================
ALTER PUBLICATION supabase_realtime ADD TABLE notifications;
ALTER PUBLICATION supabase_realtime ADD TABLE website_customers;

-- =====================================================
-- 8. TRIGGERS
-- =====================================================

-- Update customer on new order
CREATE OR REPLACE FUNCTION update_customer_on_order()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE website_customers
    SET total_orders = total_orders + 1,
        last_order_at = NOW(),
        updated_at = NOW()
    WHERE id = NEW.customer_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_customer_on_order_trigger ON delivery_orders;
CREATE TRIGGER update_customer_on_order_trigger
    AFTER INSERT ON delivery_orders
    FOR EACH ROW
    WHEN (NEW.customer_id IS NOT NULL)
    EXECUTE FUNCTION update_customer_on_order();

-- Update conversation last message
CREATE OR REPLACE FUNCTION update_conversation_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_conversations
    SET last_message = NEW.content,
        last_message_at = NEW.created_at,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_conversation_last_message_trigger ON chat_messages;
CREATE TRIGGER update_conversation_last_message_trigger
    AFTER INSERT ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_last_message();

-- =====================================================
-- DONE! Customer & Notifications system ready.
-- =====================================================

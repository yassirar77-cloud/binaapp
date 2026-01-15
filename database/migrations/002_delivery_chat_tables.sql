-- =============================================================================
-- DELIVERY ORDERS & CHAT MIGRATION
-- =============================================================================
-- This migration adds tables for delivery order management and chat conversations
-- Required for mobile delivery order submission functionality
-- =============================================================================

-- Enable UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- DELIVERY ORDERS TABLE
-- =============================================================================
-- Stores delivery orders placed through published websites

CREATE TABLE IF NOT EXISTS public.delivery_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number TEXT UNIQUE NOT NULL,
    website_id TEXT,

    -- Customer Information
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_id TEXT,  -- Optional customer identifier
    delivery_address TEXT NOT NULL,
    delivery_area TEXT,  -- e.g., "Bandar Sunway", "Petaling Jaya"

    -- Order Details
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT,

    -- Pricing
    subtotal DECIMAL(10, 2) DEFAULT 0,
    delivery_fee DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) DEFAULT 0,

    -- Order Status
    status TEXT NOT NULL DEFAULT 'pending',
    payment_method TEXT DEFAULT 'cash',
    delivery_zone_id TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for delivery_orders
CREATE INDEX IF NOT EXISTS idx_delivery_orders_website_id ON public.delivery_orders(website_id);
CREATE INDEX IF NOT EXISTS idx_delivery_orders_status ON public.delivery_orders(status);
CREATE INDEX IF NOT EXISTS idx_delivery_orders_order_number ON public.delivery_orders(order_number);
CREATE INDEX IF NOT EXISTS idx_delivery_orders_customer_phone ON public.delivery_orders(customer_phone);
CREATE INDEX IF NOT EXISTS idx_delivery_orders_created_at ON public.delivery_orders(created_at DESC);

-- Enable RLS on delivery_orders
ALTER TABLE public.delivery_orders ENABLE ROW LEVEL SECURITY;

-- RLS Policies for delivery_orders (public access for customers to create/view orders)
CREATE POLICY IF NOT EXISTS "Anyone can create delivery orders"
    ON public.delivery_orders FOR INSERT
    WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Anyone can view delivery orders"
    ON public.delivery_orders FOR SELECT
    USING (true);

CREATE POLICY IF NOT EXISTS "Anyone can update delivery orders"
    ON public.delivery_orders FOR UPDATE
    USING (true);


-- =============================================================================
-- CHAT CONVERSATIONS TABLE
-- =============================================================================
-- Stores chat conversations linked to orders or general inquiries

CREATE TABLE IF NOT EXISTS public.chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id TEXT,
    order_id TEXT,  -- Optional link to delivery_orders

    -- Customer Information
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_id TEXT,  -- Generated from phone hash if not provided

    -- Conversation Status
    status TEXT NOT NULL DEFAULT 'active',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for chat_conversations
CREATE INDEX IF NOT EXISTS idx_chat_conversations_website_id ON public.chat_conversations(website_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_customer_id ON public.chat_conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_order_id ON public.chat_conversations(order_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_status ON public.chat_conversations(status);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_updated_at ON public.chat_conversations(updated_at DESC);

-- Enable RLS on chat_conversations
ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_conversations (public access)
CREATE POLICY IF NOT EXISTS "Anyone can create chat conversations"
    ON public.chat_conversations FOR INSERT
    WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Anyone can view chat conversations"
    ON public.chat_conversations FOR SELECT
    USING (true);

CREATE POLICY IF NOT EXISTS "Anyone can update chat conversations"
    ON public.chat_conversations FOR UPDATE
    USING (true);


-- =============================================================================
-- CHAT MESSAGES TABLE
-- =============================================================================
-- Stores individual messages within chat conversations

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES public.chat_conversations(id) ON DELETE CASCADE,

    -- Message Details
    sender_type TEXT NOT NULL,  -- 'customer' or 'business'
    sender_id TEXT,
    message TEXT NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for chat_messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON public.chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON public.chat_messages(created_at DESC);

-- Enable RLS on chat_messages
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_messages (public access)
CREATE POLICY IF NOT EXISTS "Anyone can create chat messages"
    ON public.chat_messages FOR INSERT
    WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Anyone can view chat messages"
    ON public.chat_messages FOR SELECT
    USING (true);


-- =============================================================================
-- WEBSITE CUSTOMERS TABLE (Optional - for tracking customers)
-- =============================================================================
-- Stores customer information for websites

CREATE TABLE IF NOT EXISTS public.website_customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id TEXT NOT NULL,

    -- Customer Information
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,

    -- Computed customer_id from phone hash
    customer_hash TEXT,

    -- Stats
    total_orders INTEGER DEFAULT 0,
    last_order_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint on website + phone
    UNIQUE(website_id, phone)
);

-- Indexes for website_customers
CREATE INDEX IF NOT EXISTS idx_website_customers_website_id ON public.website_customers(website_id);
CREATE INDEX IF NOT EXISTS idx_website_customers_phone ON public.website_customers(phone);
CREATE INDEX IF NOT EXISTS idx_website_customers_customer_hash ON public.website_customers(customer_hash);

-- Enable RLS on website_customers
ALTER TABLE public.website_customers ENABLE ROW LEVEL SECURITY;

-- RLS Policies for website_customers (public access)
CREATE POLICY IF NOT EXISTS "Anyone can create website customers"
    ON public.website_customers FOR INSERT
    WITH CHECK (true);

CREATE POLICY IF NOT EXISTS "Anyone can view website customers"
    ON public.website_customers FOR SELECT
    USING (true);

CREATE POLICY IF NOT EXISTS "Anyone can update website customers"
    ON public.website_customers FOR UPDATE
    USING (true);


-- =============================================================================
-- UPDATED_AT TRIGGERS
-- =============================================================================

-- Function to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_delivery_orders_updated_at ON public.delivery_orders;
CREATE TRIGGER update_delivery_orders_updated_at
    BEFORE UPDATE ON public.delivery_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_chat_conversations_updated_at ON public.chat_conversations;
CREATE TRIGGER update_chat_conversations_updated_at
    BEFORE UPDATE ON public.chat_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_website_customers_updated_at ON public.website_customers;
CREATE TRIGGER update_website_customers_updated_at
    BEFORE UPDATE ON public.website_customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- DONE
-- =============================================================================
-- Run this migration on your Supabase database.
-- After running, refresh the schema cache:
-- Supabase Dashboard -> Settings -> API -> Reload Schema

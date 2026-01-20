-- =====================================================
-- DIAGNOSE AND FIX CHAT SCHEMA ISSUES
-- =====================================================
-- This migration diagnoses and fixes fundamental schema mismatches in chat tables
--
-- Issues addressed:
-- 1. BIGINT vs UUID column types
-- 2. Missing chat_participants table
-- 3. Missing columns in chat_messages
-- 4. Schema cache issues
--
-- Run this in Supabase SQL Editor
-- =====================================================

-- =====================================================
-- PART 1: DIAGNOSTIC - Check current state
-- =====================================================

DO $$
DECLARE
    table_exists BOOLEAN;
    col_type TEXT;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'CHAT SCHEMA DIAGNOSTIC';
    RAISE NOTICE '========================================';

    -- Check chat_conversations
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'chat_conversations'
    ) INTO table_exists;

    IF table_exists THEN
        RAISE NOTICE '✓ chat_conversations exists';

        -- Check ID type
        SELECT data_type INTO col_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chat_conversations'
        AND column_name = 'id';

        RAISE NOTICE '  - id column type: %', col_type;
    ELSE
        RAISE WARNING '✗ chat_conversations does NOT exist';
    END IF;

    -- Check chat_messages
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'chat_messages'
    ) INTO table_exists;

    IF table_exists THEN
        RAISE NOTICE '✓ chat_messages exists';

        -- Check ID type
        SELECT data_type INTO col_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
        AND column_name = 'id';

        RAISE NOTICE '  - id column type: %', col_type;

        -- Check conversation_id type
        SELECT data_type INTO col_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'chat_messages'
        AND column_name = 'conversation_id';

        RAISE NOTICE '  - conversation_id column type: %', col_type;
    ELSE
        RAISE WARNING '✗ chat_messages does NOT exist';
    END IF;

    -- Check chat_participants
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'chat_participants'
    ) INTO table_exists;

    IF table_exists THEN
        RAISE NOTICE '✓ chat_participants exists';
    ELSE
        RAISE WARNING '✗ chat_participants does NOT exist';
    END IF;

    RAISE NOTICE '========================================';
END $$;

-- =====================================================
-- PART 2: FIX STRATEGY
-- =====================================================
-- Based on diagnostic above, uncomment the appropriate fix section

-- =====================================================
-- FIX A: If tables DON'T exist - Create from scratch
-- =====================================================
-- Uncomment this section if chat tables don't exist

/*
-- Create chat_conversations with UUID
CREATE TABLE IF NOT EXISTS public.chat_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES public.delivery_orders(id) ON DELETE SET NULL,
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,
    customer_id TEXT NOT NULL,
    customer_name TEXT,
    customer_phone TEXT,
    website_name TEXT,
    status TEXT DEFAULT 'active',
    unread_owner INTEGER DEFAULT 0,
    unread_customer INTEGER DEFAULT 0,
    unread_rider INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create chat_messages with UUID
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.chat_conversations(id) ON DELETE CASCADE NOT NULL,
    sender_type TEXT NOT NULL,
    sender_id TEXT,
    message_type TEXT DEFAULT 'text',
    message_text TEXT NOT NULL DEFAULT '',
    content TEXT,
    media_url TEXT,
    metadata JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create chat_participants
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_chat_conversations_website ON public.chat_conversations(website_id);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_customer ON public.chat_conversations(customer_phone);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_status ON public.chat_conversations(status);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON public.chat_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON public.chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_participants_conversation ON public.chat_participants(conversation_id);

-- Enable RLS
ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_participants ENABLE ROW LEVEL SECURITY;

-- Create policies (permissive for now)
DROP POLICY IF EXISTS "Allow all chat_conversations" ON public.chat_conversations;
CREATE POLICY "Allow all chat_conversations" ON public.chat_conversations
FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all chat_messages" ON public.chat_messages;
CREATE POLICY "Allow all chat_messages" ON public.chat_messages
FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all chat_participants" ON public.chat_participants;
CREATE POLICY "Allow all chat_participants" ON public.chat_participants
FOR ALL USING (true) WITH CHECK (true);

-- Grant permissions
GRANT ALL ON public.chat_conversations TO service_role, authenticated, anon;
GRANT ALL ON public.chat_messages TO service_role, authenticated, anon;
GRANT ALL ON public.chat_participants TO service_role, authenticated, anon;

-- Enable realtime
ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_conversations;
ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_participants;

RAISE NOTICE '✅ Created chat tables with UUID from scratch';
*/

-- =====================================================
-- FIX B: If tables exist with BIGINT - Recreate them
-- =====================================================
-- DANGER: This will DROP existing tables and recreate with UUID
-- Uncomment ONLY if you're OK losing existing chat data

/*
-- Backup data first (optional)
-- CREATE TABLE chat_conversations_backup AS SELECT * FROM chat_conversations;
-- CREATE TABLE chat_messages_backup AS SELECT * FROM chat_messages;

-- Drop existing tables (CASCADE removes dependent objects)
DROP TABLE IF EXISTS public.chat_participants CASCADE;
DROP TABLE IF EXISTS public.chat_messages CASCADE;
DROP TABLE IF EXISTS public.chat_conversations CASCADE;

-- Now run FIX A section above to recreate tables

RAISE NOTICE '⚠️ Dropped and recreated chat tables - OLD DATA LOST';
*/

-- =====================================================
-- FIX C: Add missing chat_participants table only
-- =====================================================
-- Uncomment this if chat_participants is the only missing table

/*
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

CREATE INDEX IF NOT EXISTS idx_chat_participants_conversation ON public.chat_participants(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_participants_user ON public.chat_participants(user_type, user_id);

ALTER TABLE public.chat_participants ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all chat_participants" ON public.chat_participants;
CREATE POLICY "Allow all chat_participants" ON public.chat_participants
FOR ALL USING (true) WITH CHECK (true);

GRANT ALL ON public.chat_participants TO service_role, authenticated, anon;

ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_participants;

RAISE NOTICE '✅ Created chat_participants table';
*/

-- =====================================================
-- PART 3: RELOAD SCHEMA CACHE
-- =====================================================
-- Always run this at the end
NOTIFY pgrst, 'reload schema';
RAISE NOTICE '✅ Schema cache reloaded';

-- =====================================================
-- PART 4: VERIFICATION
-- =====================================================

DO $$
DECLARE
    conversations_type TEXT;
    messages_id_type TEXT;
    messages_conv_type TEXT;
    participants_exists BOOLEAN;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'VERIFICATION';
    RAISE NOTICE '========================================';

    -- Check chat_conversations id type
    SELECT data_type INTO conversations_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_conversations'
    AND column_name = 'id';

    IF conversations_type = 'uuid' THEN
        RAISE NOTICE '✓ chat_conversations.id is UUID';
    ELSE
        RAISE WARNING '✗ chat_conversations.id is % (should be UUID)', conversations_type;
    END IF;

    -- Check chat_messages id type
    SELECT data_type INTO messages_id_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
    AND column_name = 'id';

    IF messages_id_type = 'uuid' THEN
        RAISE NOTICE '✓ chat_messages.id is UUID';
    ELSE
        RAISE WARNING '✗ chat_messages.id is % (should be UUID)', messages_id_type;
    END IF;

    -- Check chat_messages conversation_id type
    SELECT data_type INTO messages_conv_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
    AND column_name = 'conversation_id';

    IF messages_conv_type = 'uuid' THEN
        RAISE NOTICE '✓ chat_messages.conversation_id is UUID';
    ELSE
        RAISE WARNING '✗ chat_messages.conversation_id is % (should be UUID)', messages_conv_type;
    END IF;

    -- Check chat_participants exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'chat_participants'
    ) INTO participants_exists;

    IF participants_exists THEN
        RAISE NOTICE '✓ chat_participants table exists';
    ELSE
        RAISE WARNING '✗ chat_participants table missing';
    END IF;

    RAISE NOTICE '========================================';
END $$;

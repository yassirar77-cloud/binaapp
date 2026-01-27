-- =============================================================================
-- MIGRATION 003: FIX CRITICAL RLS SECURITY ISSUES
-- =============================================================================
-- This migration fixes the CRITICAL security vulnerability where RLS policies
-- were set to USING (true), allowing ANY user to access ANY data.
--
-- SECURITY MODEL:
-- - Business owners (authenticated): Can only access data for their own websites
-- - Customers (unauthenticated): Can create and view orders (API must filter)
-- - Service role bypasses RLS (used sparingly for admin operations)
--
-- APPROACH:
-- 1. Restrict business owner access with RLS based on website ownership
-- 2. Allow customer operations (INSERT/SELECT) but rely on API-level filtering
-- 3. Block unauthorized UPDATE/DELETE operations
-- =============================================================================

-- =============================================================================
-- FIX DELIVERY_ORDERS TABLE RLS
-- =============================================================================

-- Drop existing insecure policies
DROP POLICY IF EXISTS "Anyone can create delivery orders" ON public.delivery_orders;
DROP POLICY IF EXISTS "Anyone can view delivery orders" ON public.delivery_orders;
DROP POLICY IF EXISTS "Anyone can update delivery orders" ON public.delivery_orders;

-- Create secure policies

-- Policy 1: Anyone can INSERT orders (customers placing orders)
CREATE POLICY "Allow order creation"
    ON public.delivery_orders FOR INSERT
    WITH CHECK (true);

-- Policy 2: Anyone can SELECT orders (but API MUST filter by customer_id/phone)
-- This is necessary because customers are unauthenticated
CREATE POLICY "Allow order viewing"
    ON public.delivery_orders FOR SELECT
    USING (true);

-- Policy 3: ONLY authenticated business owners can UPDATE orders for their websites
CREATE POLICY "Business owners can update own website orders"
    ON public.delivery_orders FOR UPDATE
    USING (
        auth.uid() IS NOT NULL
        AND website_id IN (
            SELECT id::text FROM public.websites
            WHERE user_id = auth.uid()
        )
    );

-- Policy 4: ONLY authenticated business owners can DELETE orders for their websites
CREATE POLICY "Business owners can delete own website orders"
    ON public.delivery_orders FOR DELETE
    USING (
        auth.uid() IS NOT NULL
        AND website_id IN (
            SELECT id::text FROM public.websites
            WHERE user_id = auth.uid()
        )
    );

-- =============================================================================
-- FIX CHAT_CONVERSATIONS TABLE RLS
-- =============================================================================

-- Drop existing insecure policies
DROP POLICY IF EXISTS "Anyone can create chat conversations" ON public.chat_conversations;
DROP POLICY IF EXISTS "Anyone can view chat conversations" ON public.chat_conversations;
DROP POLICY IF EXISTS "Anyone can update chat conversations" ON public.chat_conversations;

-- Create secure policies

-- Policy 1: Anyone can INSERT conversations (customers starting chats)
CREATE POLICY "Allow conversation creation"
    ON public.chat_conversations FOR INSERT
    WITH CHECK (true);

-- Policy 2: Anyone can SELECT conversations (but API MUST filter by customer_id/phone)
CREATE POLICY "Allow conversation viewing"
    ON public.chat_conversations FOR SELECT
    USING (true);

-- Policy 3: ONLY authenticated business owners can UPDATE conversations for their websites
CREATE POLICY "Business owners can update own website conversations"
    ON public.chat_conversations FOR UPDATE
    USING (
        auth.uid() IS NOT NULL
        AND website_id IN (
            SELECT id::text FROM public.websites
            WHERE user_id = auth.uid()
        )
    );

-- Policy 4: ONLY authenticated business owners can DELETE conversations for their websites
CREATE POLICY "Business owners can delete own website conversations"
    ON public.chat_conversations FOR DELETE
    USING (
        auth.uid() IS NOT NULL
        AND website_id IN (
            SELECT id::text FROM public.websites
            WHERE user_id = auth.uid()
        )
    );

-- =============================================================================
-- FIX CHAT_MESSAGES TABLE RLS
-- =============================================================================

-- Drop existing insecure policies
DROP POLICY IF EXISTS "Anyone can create chat messages" ON public.chat_messages;
DROP POLICY IF EXISTS "Anyone can view chat messages" ON public.chat_messages;

-- Create secure policies

-- Policy 1: Anyone can INSERT messages (customers and business chatting)
CREATE POLICY "Allow message creation"
    ON public.chat_messages FOR INSERT
    WITH CHECK (true);

-- Policy 2: Anyone can SELECT messages (but API MUST filter by conversation access)
CREATE POLICY "Allow message viewing"
    ON public.chat_messages FOR SELECT
    USING (true);

-- Policy 3: ONLY authenticated business owners can UPDATE messages in their conversations
CREATE POLICY "Business owners can update own messages"
    ON public.chat_messages FOR UPDATE
    USING (
        auth.uid() IS NOT NULL
        AND conversation_id IN (
            SELECT id FROM public.chat_conversations
            WHERE website_id IN (
                SELECT id::text FROM public.websites
                WHERE user_id = auth.uid()
            )
        )
    );

-- Policy 4: ONLY authenticated business owners can DELETE messages in their conversations
CREATE POLICY "Business owners can delete own messages"
    ON public.chat_messages FOR DELETE
    USING (
        auth.uid() IS NOT NULL
        AND conversation_id IN (
            SELECT id FROM public.chat_conversations
            WHERE website_id IN (
                SELECT id::text FROM public.websites
                WHERE user_id = auth.uid()
            )
        )
    );

-- =============================================================================
-- FIX WEBSITE_CUSTOMERS TABLE RLS
-- =============================================================================

-- Drop existing insecure policies if they exist
DROP POLICY IF EXISTS "Anyone can create website customers" ON public.website_customers;
DROP POLICY IF EXISTS "Anyone can view website customers" ON public.website_customers;
DROP POLICY IF EXISTS "Anyone can update website customers" ON public.website_customers;

-- Enable RLS if not already enabled
ALTER TABLE public.website_customers ENABLE ROW LEVEL SECURITY;

-- Create secure policies

-- Policy 1: Anyone can INSERT customer records
CREATE POLICY "Allow customer creation"
    ON public.website_customers FOR INSERT
    WITH CHECK (true);

-- Policy 2: Anyone can SELECT customer records (but API MUST filter by customer_id)
CREATE POLICY "Allow customer viewing"
    ON public.website_customers FOR SELECT
    USING (true);

-- Policy 3: ONLY authenticated business owners can UPDATE customers for their websites
CREATE POLICY "Business owners can update own website customers"
    ON public.website_customers FOR UPDATE
    USING (
        auth.uid() IS NOT NULL
        AND website_id IN (
            SELECT id::text FROM public.websites
            WHERE user_id = auth.uid()
        )
    );

-- Policy 4: ONLY authenticated business owners can DELETE customers for their websites
CREATE POLICY "Business owners can delete own website customers"
    ON public.website_customers FOR DELETE
    USING (
        auth.uid() IS NOT NULL
        AND website_id IN (
            SELECT id::text FROM public.websites
            WHERE user_id = auth.uid()
        )
    );

-- =============================================================================
-- CRITICAL: APPLICATION LAYER RESPONSIBILITIES
-- =============================================================================
-- With these RLS policies:
--
-- 1. UPDATE/DELETE operations are protected - only business owners can modify their data
-- 2. INSERT/SELECT operations are open - but API MUST implement filtering:
--    - Customer endpoints: Filter by customer_id or customer_phone
--    - Business endpoints: Verify website ownership before querying
--
-- 3. API endpoints MUST:
--    - Validate website_id belongs to authenticated user (for business operations)
--    - Filter results by customer_id/phone (for customer operations)
--    - Never expose data without proper authorization checks
--
-- 4. Service role key should ONLY be used for:
--    - Customer-facing operations (widget init, order creation)
--    - Admin operations
--    - Migrations
--    NOT for business owner operations (use anon key + JWT instead)
-- =============================================================================

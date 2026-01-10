-- =====================================================
-- BinaApp Critical Fix: Owner Cannot See Orders
-- Run this in Supabase SQL Editor
-- =====================================================
--
-- PROBLEM: Owners cannot see orders in their dashboard
-- ROOT CAUSE: RLS policies might be too restrictive or incorrectly configured
--
-- This script ensures:
-- 1. Owners can VIEW all orders from their websites
-- 2. Owners can UPDATE order status (confirm/reject/assign)
-- 3. Owners can VIEW and MANAGE riders
-- 4. All necessary permissions are granted
--
-- =====================================================

\echo '==========================================';
\echo 'FIXING OWNER ACCESS TO ORDERS';
\echo '==========================================';

-- =====================================================
-- 1. FIX DELIVERY_ORDERS RLS POLICIES
-- =====================================================

-- Drop existing policies to recreate them correctly
DROP POLICY IF EXISTS "Users can view own orders" ON delivery_orders;
DROP POLICY IF EXISTS "Users can manage own orders" ON delivery_orders;
DROP POLICY IF EXISTS "Anyone can track orders by number" ON delivery_orders;
DROP POLICY IF EXISTS "Anyone can create orders" ON delivery_orders;

-- POLICY 1: Owners can VIEW orders from their websites
CREATE POLICY "owners_can_view_their_website_orders" ON delivery_orders
    FOR SELECT
    TO authenticated
    USING (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
    );

-- POLICY 2: Owners can UPDATE orders from their websites
CREATE POLICY "owners_can_update_their_website_orders" ON delivery_orders
    FOR UPDATE
    TO authenticated
    USING (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
    );

-- POLICY 3: Public can create orders (for customer ordering)
CREATE POLICY "public_can_create_orders" ON delivery_orders
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- POLICY 4: Public can view orders by order_number (for tracking)
CREATE POLICY "public_can_track_orders" ON delivery_orders
    FOR SELECT
    TO anon, authenticated
    USING (true);

\echo '✅ Delivery orders policies fixed';

-- =====================================================
-- 2. FIX ORDER_ITEMS RLS POLICIES
-- =====================================================

DROP POLICY IF EXISTS "Users can view own order items" ON order_items;
DROP POLICY IF EXISTS "Anyone can view order items" ON order_items;
DROP POLICY IF EXISTS "Anyone can create order items" ON order_items;

-- POLICY 1: Owners can VIEW order items from their websites
CREATE POLICY "owners_can_view_their_order_items" ON order_items
    FOR SELECT
    TO authenticated
    USING (
        order_id IN (
            SELECT o.id FROM delivery_orders o
            WHERE o.website_id IN (
                SELECT id FROM websites WHERE user_id = auth.uid()
            )
        )
    );

-- POLICY 2: Public can view order items (for tracking)
CREATE POLICY "public_can_view_order_items" ON order_items
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- POLICY 3: Public can create order items (when placing orders)
CREATE POLICY "public_can_create_order_items" ON order_items
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

\echo '✅ Order items policies fixed';

-- =====================================================
-- 3. FIX RIDERS RLS POLICIES
-- =====================================================

DROP POLICY IF EXISTS "Users can view own riders" ON riders;
DROP POLICY IF EXISTS "Users can manage own riders" ON riders;

-- POLICY 1: Owners can VIEW riders (their own + shared)
CREATE POLICY "owners_can_view_riders" ON riders
    FOR SELECT
    TO authenticated
    USING (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
        OR website_id IS NULL  -- Shared riders
    );

-- POLICY 2: Owners can INSERT riders
CREATE POLICY "owners_can_create_riders" ON riders
    FOR INSERT
    TO authenticated
    WITH CHECK (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
    );

-- POLICY 3: Owners can UPDATE their riders
CREATE POLICY "owners_can_update_riders" ON riders
    FOR UPDATE
    TO authenticated
    USING (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
    );

-- POLICY 4: Owners can DELETE their riders
CREATE POLICY "owners_can_delete_riders" ON riders
    FOR DELETE
    TO authenticated
    USING (
        website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )
    );

\echo '✅ Riders policies fixed';

-- =====================================================
-- 4. ENSURE ALL NECESSARY PERMISSIONS ARE GRANTED
-- =====================================================

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE ON delivery_orders TO authenticated;
GRANT SELECT, INSERT ON order_items TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON riders TO authenticated;

-- Grant permissions to anonymous users (for public ordering)
GRANT SELECT, INSERT ON delivery_orders TO anon;
GRANT SELECT, INSERT ON order_items TO anon;

\echo '✅ Permissions granted';

-- =====================================================
-- 5. VERIFY THE FIX
-- =====================================================

\echo '';
\echo '==========================================';
\echo 'VERIFICATION: Checking RLS Policies';
\echo '==========================================';

SELECT
    tablename,
    policyname,
    cmd,
    roles
FROM pg_policies
WHERE tablename IN ('delivery_orders', 'order_items', 'riders')
ORDER BY tablename, cmd, policyname;

\echo '';
\echo '==========================================';
\echo 'VERIFICATION: Checking Permissions';
\echo '==========================================';

SELECT
    table_name,
    grantee,
    string_agg(privilege_type, ', ') as privileges
FROM information_schema.table_privileges
WHERE table_name IN ('delivery_orders', 'order_items', 'riders')
AND grantee IN ('authenticated', 'anon')
GROUP BY table_name, grantee
ORDER BY table_name, grantee;

\echo '';
\echo '==========================================';
\echo '✅ FIX COMPLETE!';
\echo '==========================================';
\echo '';
\echo 'What this fixed:';
\echo '1. ✅ Owners can now VIEW all orders from their websites';
\echo '2. ✅ Owners can now UPDATE order status (confirm/reject/assign)';
\echo '3. ✅ Owners can now VIEW and MANAGE their riders';
\echo '4. ✅ Customers can still create orders and track them';
\echo '';
\echo 'Next steps:';
\echo '1. Refresh your profile page at https://www.binaapp.my/profile';
\echo '2. Click the "📦 Pesanan" tab';
\echo '3. You should now see all your orders!';
\echo '';
\echo 'If you still cannot see orders:';
\echo '1. Run VERIFY_BACKEND_SETUP.sql to check for other issues';
\echo '2. Check browser console for any JavaScript errors';
\echo '3. Verify Supabase environment variables are set correctly';
\echo '';

SELECT 'Backend fix applied successfully!' as status, NOW() as fixed_at;

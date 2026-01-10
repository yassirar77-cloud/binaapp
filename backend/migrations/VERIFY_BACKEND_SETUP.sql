-- =====================================================
-- BinaApp Backend Verification Script
-- Run this in Supabase SQL Editor to verify backend setup
-- =====================================================

\echo '==========================================';
\echo '1. CHECKING IF TABLES EXIST';
\echo '==========================================';

SELECT
    tablename,
    CASE
        WHEN tablename IN (
            'delivery_orders', 'order_items', 'riders',
            'delivery_zones', 'menu_categories', 'menu_items',
            'order_status_history', 'rider_locations', 'delivery_settings'
        ) THEN '✅ EXISTS'
        ELSE '❌ MISSING'
    END as status
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
    'delivery_orders', 'order_items', 'riders',
    'delivery_zones', 'menu_categories', 'menu_items',
    'order_status_history', 'rider_locations', 'delivery_settings',
    'websites', 'profiles'
)
ORDER BY tablename;

\echo '';
\echo '==========================================';
\echo '2. CHECKING RLS (Row Level Security) STATUS';
\echo '==========================================';

SELECT
    tablename,
    CASE WHEN rowsecurity THEN '✅ ENABLED' ELSE '❌ DISABLED' END as rls_status
FROM pg_tables t
JOIN pg_class c ON c.relname = t.tablename
WHERE schemaname = 'public'
AND tablename IN (
    'delivery_orders', 'order_items', 'riders',
    'delivery_zones', 'menu_items', 'menu_categories'
)
ORDER BY tablename;

\echo '';
\echo '==========================================';
\echo '3. CHECKING PERMISSIONS FOR AUTHENTICATED USERS';
\echo '==========================================';

SELECT
    table_name,
    privilege_type,
    CASE
        WHEN grantee = 'authenticated' THEN '✅ GRANTED'
        ELSE '⚠️  NOT GRANTED'
    END as status
FROM information_schema.table_privileges
WHERE table_name IN ('delivery_orders', 'order_items', 'riders')
AND grantee IN ('authenticated', 'anon')
ORDER BY table_name, grantee, privilege_type;

\echo '';
\echo '==========================================';
\echo '4. CHECKING RLS POLICIES FOR DELIVERY_ORDERS';
\echo '==========================================';

SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    CASE
        WHEN policyname LIKE '%own%' THEN '✅ OWNER ACCESS'
        WHEN policyname LIKE '%public%' OR policyname LIKE '%anyone%' THEN '✅ PUBLIC ACCESS'
        ELSE '⚠️  CHECK POLICY'
    END as policy_type
FROM pg_policies
WHERE tablename IN ('delivery_orders', 'order_items', 'riders')
ORDER BY tablename, policyname;

\echo '';
\echo '==========================================';
\echo '5. CHECKING IF THERE ARE ANY ORDERS';
\echo '==========================================';

SELECT
    COUNT(*) as total_orders,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
    COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_orders,
    COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered_orders,
    MAX(created_at) as latest_order_time
FROM delivery_orders;

\echo '';
\echo '==========================================';
\echo '6. SAMPLE OF RECENT ORDERS';
\echo '==========================================';

SELECT
    order_number,
    status,
    customer_name,
    total_amount,
    created_at,
    CASE
        WHEN website_id IS NULL THEN '❌ NO WEBSITE'
        ELSE '✅ HAS WEBSITE'
    END as website_status
FROM delivery_orders
ORDER BY created_at DESC
LIMIT 5;

\echo '';
\echo '==========================================';
\echo '7. CHECKING IF THERE ARE ANY RIDERS';
\echo '==========================================';

SELECT
    COUNT(*) as total_riders,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_riders,
    COUNT(CASE WHEN is_online = true THEN 1 END) as online_riders,
    COUNT(CASE WHEN website_id IS NOT NULL THEN 1 END) as riders_with_website
FROM riders;

\echo '';
\echo '==========================================';
\echo '8. SAMPLE OF RIDERS';
\echo '==========================================';

SELECT
    name,
    phone,
    vehicle_type,
    is_active,
    is_online,
    CASE
        WHEN website_id IS NULL THEN '⚠️  SHARED RIDER'
        ELSE '✅ WEBSITE RIDER'
    END as rider_type
FROM riders
LIMIT 5;

\echo '';
\echo '==========================================';
\echo '9. CHECKING WEBSITES FOR ORDERS';
\echo '==========================================';

SELECT
    w.id,
    w.name,
    w.subdomain,
    COUNT(DISTINCT o.id) as total_orders,
    COUNT(DISTINCT r.id) as total_riders
FROM websites w
LEFT JOIN delivery_orders o ON o.website_id = w.id
LEFT JOIN riders r ON r.website_id = w.id
GROUP BY w.id, w.name, w.subdomain
ORDER BY total_orders DESC
LIMIT 10;

\echo '';
\echo '==========================================';
\echo '10. CHECKING FOR MISSING RLS POLICIES';
\echo '==========================================';

-- Check if authenticated users can SELECT their own orders
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = 'delivery_orders'
            AND policyname LIKE '%own%'
            AND 'authenticated' = ANY(roles)
            AND cmd = 'SELECT'
        ) THEN '✅ Users can view own orders'
        ELSE '❌ MISSING: Users cannot view own orders policy'
    END as policy_status;

-- Check if authenticated users can UPDATE their own orders
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = 'delivery_orders'
            AND policyname LIKE '%own%'
            AND 'authenticated' = ANY(roles)
            AND cmd = 'UPDATE'
        ) THEN '✅ Users can update own orders'
        ELSE '❌ MISSING: Users cannot update own orders policy'
    END as policy_status;

\echo '';
\echo '==========================================';
\echo '11. CRITICAL: CHECK IF OWNER CAN SEE ORDERS';
\echo '==========================================';

-- This checks if the RLS policy correctly links orders to website owners
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = 'delivery_orders'
            AND qual LIKE '%user_id = auth.uid()%'
        ) THEN '✅ Owners can see orders via user_id'
        WHEN EXISTS (
            SELECT 1 FROM pg_policies
            WHERE tablename = 'delivery_orders'
            AND qual LIKE '%website_id IN%'
        ) THEN '✅ Owners can see orders via website_id'
        ELSE '❌ CRITICAL: No policy for owners to see their orders!'
    END as critical_check;

\echo '';
\echo '==========================================';
\echo '12. VERIFICATION SUMMARY';
\echo '==========================================';

SELECT
    'Backend Setup Verification Complete' as status,
    NOW() as checked_at;

\echo '';
\echo 'If you see ❌ or ⚠️  symbols above, those need to be fixed!';
\echo '';

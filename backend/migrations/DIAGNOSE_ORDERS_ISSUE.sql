-- =====================================================
-- BinaApp Quick Diagnostic: Why Can't I See Orders?
-- Run this in Supabase SQL Editor
-- Replace 'YOUR_USER_ID' with your actual user ID
-- =====================================================
--
-- To find your user ID, run:
-- SELECT auth.uid();
-- (when logged in via Supabase dashboard)
--
-- Or check in your browser's Network tab when loading profile page
--
-- =====================================================

\echo '==========================================';
\echo 'DIAGNOSTIC 1: Do you have any websites?';
\echo '==========================================';

-- Replace YOUR_USER_ID with your actual user ID
SELECT
    id as website_id,
    name as website_name,
    subdomain,
    created_at
FROM websites
WHERE user_id = auth.uid()  -- This will use your current logged-in user
ORDER BY created_at DESC;

-- If the above returns empty, try:
-- WHERE user_id = 'YOUR_USER_ID'  -- Replace with actual UUID

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 2: Are there ANY orders?';
\echo '==========================================';

SELECT
    COUNT(*) as total_orders,
    COUNT(DISTINCT website_id) as websites_with_orders
FROM delivery_orders;

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 3: Orders breakdown by status';
\echo '==========================================';

SELECT
    status,
    COUNT(*) as count,
    MAX(created_at) as latest_order
FROM delivery_orders
GROUP BY status
ORDER BY count DESC;

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 4: Can you see orders via RLS?';
\echo '==========================================';

-- This simulates what the frontend query does
SELECT
    o.id,
    o.order_number,
    o.status,
    o.customer_name,
    o.total_amount,
    o.created_at,
    o.website_id,
    w.name as website_name
FROM delivery_orders o
LEFT JOIN websites w ON w.id = o.website_id
WHERE o.website_id IN (
    SELECT id FROM websites WHERE user_id = auth.uid()
)
ORDER BY o.created_at DESC
LIMIT 10;

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 5: Recent orders (all)';
\echo '==========================================';

-- This shows ALL recent orders (admin view)
-- If you can see orders here but not in DIAGNOSTIC 4,
-- then the RLS policy is the problem
SELECT
    order_number,
    status,
    customer_name,
    total_amount,
    website_id,
    created_at
FROM delivery_orders
ORDER BY created_at DESC
LIMIT 5;

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 6: Are there riders?';
\echo '==========================================';

SELECT
    COUNT(*) as total_riders,
    COUNT(CASE WHEN website_id IN (
        SELECT id FROM websites WHERE user_id = auth.uid()
    ) THEN 1 END) as your_riders,
    COUNT(CASE WHEN website_id IS NULL THEN 1 END) as shared_riders
FROM riders;

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 7: Sample riders';
\echo '==========================================';

SELECT
    r.id,
    r.name,
    r.phone,
    r.is_active,
    r.is_online,
    CASE
        WHEN r.website_id IS NULL THEN 'SHARED'
        ELSE w.name
    END as owner
FROM riders r
LEFT JOIN websites w ON w.id = r.website_id
WHERE r.is_active = true
LIMIT 5;

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 8: Check RLS policies';
\echo '==========================================';

SELECT
    policyname,
    cmd,
    roles,
    SUBSTRING(qual::text, 1, 80) as condition
FROM pg_policies
WHERE tablename = 'delivery_orders'
ORDER BY cmd, policyname;

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC 9: Check if table exists';
\echo '==========================================';

SELECT
    tablename,
    CASE WHEN EXISTS (
        SELECT 1 FROM delivery_orders LIMIT 1
    ) THEN '✅ Table exists and has data'
    ELSE '⚠️  Table exists but NO DATA'
    END as status
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'delivery_orders';

\echo '';
\echo '==========================================';
\echo 'DIAGNOSTIC SUMMARY';
\echo '==========================================';

SELECT
    CASE
        WHEN (SELECT COUNT(*) FROM websites WHERE user_id = auth.uid()) = 0
            THEN '❌ You have NO websites'
        WHEN (SELECT COUNT(*) FROM delivery_orders) = 0
            THEN '❌ There are NO orders in the system'
        WHEN (SELECT COUNT(*) FROM delivery_orders WHERE website_id IN (
            SELECT id FROM websites WHERE user_id = auth.uid()
        )) = 0
            THEN '❌ You have websites but NO orders for your websites (or RLS blocking access)'
        ELSE '✅ Everything looks good - orders should be visible'
    END as diagnostic_result;

\echo '';
\echo '==========================================';
\echo 'POSSIBLE SOLUTIONS BASED ON DIAGNOSTICS:';
\echo '==========================================';
\echo '';
\echo 'If DIAGNOSTIC 1 shows no websites:';
\echo '  → You need to create a website first';
\echo '';
\echo 'If DIAGNOSTIC 2 shows 0 orders:';
\echo '  → No orders have been placed yet';
\echo '  → Create a test order to verify the system works';
\echo '';
\echo 'If DIAGNOSTIC 4 shows no orders but DIAGNOSTIC 5 does:';
\echo '  → RLS policies are blocking access';
\echo '  → Run: 006_fix_owner_orders_access.sql';
\echo '';
\echo 'If DIAGNOSTIC 6 shows 0 riders:';
\echo '  → You need to add riders to deliver orders';
\echo '  → Run: 003_test_data.sql (modify with your website_id)';
\echo '';

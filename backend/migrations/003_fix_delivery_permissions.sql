-- BinaApp Delivery System - Permission Fix
-- Run this SQL in Supabase SQL Editor to fix missing permissions
-- This fixes the root cause of "delivery not working" issue

-- =====================================================
-- FIX: Add missing GRANT permissions for anonymous users
-- =====================================================

-- Allow anonymous users to view menu item options (for item customization)
GRANT SELECT ON menu_item_options TO anon;

-- CRITICAL FIX: Allow anonymous users to INSERT order items
-- Without this, orders are created but items fail to save!
GRANT INSERT ON order_items TO anon;

-- Allow anonymous users to view their order items
GRANT SELECT ON order_items TO anon;

-- Allow the status change trigger to log status changes for anonymous orders
GRANT INSERT ON order_status_history TO anon;
GRANT SELECT ON order_status_history TO anon;

-- Allow anonymous users to view delivery settings (for business hours, min order, etc.)
GRANT SELECT ON delivery_settings TO anon;

-- =====================================================
-- Verify permissions are applied
-- =====================================================
-- You can run this query to verify:
-- SELECT grantee, table_name, privilege_type 
-- FROM information_schema.table_privileges 
-- WHERE table_name IN ('order_items', 'order_status_history', 'delivery_settings', 'menu_item_options')
-- AND grantee = 'anon';

-- =====================================================
-- DONE! Delivery system should now work properly.
-- =====================================================

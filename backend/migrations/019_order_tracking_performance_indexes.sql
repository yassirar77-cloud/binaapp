-- ============================================
-- Migration 019: Order Tracking Performance Indexes
-- Purpose: Add database indexes for enterprise-scale order tracking
-- Supports 1,000-10,000+ concurrent users
-- ============================================

-- Index for order status queries (used by owners and customers)
CREATE INDEX IF NOT EXISTS idx_delivery_orders_status
ON delivery_orders(status);

-- Index for customer order lookups by phone
CREATE INDEX IF NOT EXISTS idx_delivery_orders_customer_phone
ON delivery_orders(customer_phone);

-- Index for website-specific order queries
CREATE INDEX IF NOT EXISTS idx_delivery_orders_website_id
ON delivery_orders(website_id);

-- Composite index for owner dashboard queries
-- Most common query: SELECT * FROM delivery_orders WHERE website_id = ? AND status IN (...) ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_delivery_orders_website_status_created
ON delivery_orders(website_id, status, created_at DESC);

-- Index for order number lookups (already unique, but good to have btree index)
CREATE INDEX IF NOT EXISTS idx_delivery_orders_order_number
ON delivery_orders(order_number);

-- Index for rider assignment queries
CREATE INDEX IF NOT EXISTS idx_delivery_orders_rider_id
ON delivery_orders(rider_id)
WHERE rider_id IS NOT NULL;

-- Index for order status history queries
CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id
ON order_status_history(order_id);

-- Composite index for status history timeline
CREATE INDEX IF NOT EXISTS idx_order_status_history_order_created
ON order_status_history(order_id, created_at DESC);

-- Index for rider location queries
CREATE INDEX IF NOT EXISTS idx_rider_locations_rider_order
ON rider_locations(rider_id, order_id);

-- Index for active rider queries
CREATE INDEX IF NOT EXISTS idx_riders_active_status
ON riders(status)
WHERE status = 'active';

-- Index for website rider queries
CREATE INDEX IF NOT EXISTS idx_riders_website_id
ON riders(website_id);

-- ============================================
-- Analyze tables to update statistics
-- ============================================
ANALYZE delivery_orders;
ANALYZE order_status_history;
ANALYZE rider_locations;
ANALYZE riders;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 019: Order tracking performance indexes created successfully';
END $$;

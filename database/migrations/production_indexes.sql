-- ============================================================================
-- BinaApp Production Database Indexes
-- ============================================================================
-- These indexes are recommended for production deployments with 1000+ users.
-- Run these migrations after the base schema is in place.
--
-- IMPORTANT: Test index creation on a staging environment first.
-- Large tables may require CONCURRENTLY option to avoid locking.
-- ============================================================================

-- ============================================================================
-- WEBSITES TABLE INDEXES
-- ============================================================================

-- Fast lookup by user (dashboard listings)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_websites_user_id
    ON websites(user_id);

-- Fast lookup by subdomain (subdomain routing)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_websites_subdomain
    ON websites(subdomain)
    WHERE subdomain IS NOT NULL;

-- Fast lookup by custom domain
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_websites_custom_domain
    ON websites(custom_domain)
    WHERE custom_domain IS NOT NULL;

-- Filter by status (active websites)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_websites_status
    ON websites(status);

-- Composite index for user's websites ordered by creation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_websites_user_created
    ON websites(user_id, created_at DESC);

-- Full-text search on website content (if needed)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_websites_content_search
--     ON websites USING gin(to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, '')));

-- ============================================================================
-- DELIVERY ORDERS TABLE INDEXES
-- ============================================================================

-- Fast lookup by website (business dashboard)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_orders_website_id
    ON delivery_orders(website_id);

-- Fast lookup by order number (customer tracking)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_orders_order_number
    ON delivery_orders(order_number);

-- Filter by status (pending orders, active orders)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_orders_status
    ON delivery_orders(status);

-- Fast lookup by rider (rider app)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_orders_rider_id
    ON delivery_orders(rider_id)
    WHERE rider_id IS NOT NULL;

-- Composite index for business order listings
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_orders_website_status_created
    ON delivery_orders(website_id, status, created_at DESC);

-- Composite index for finding orders in date range
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_orders_created_at
    ON delivery_orders(created_at DESC);

-- Fast lookup by customer phone (order history)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_orders_customer_phone
    ON delivery_orders(customer_phone)
    WHERE customer_phone IS NOT NULL;

-- ============================================================================
-- ORDER ITEMS TABLE INDEXES
-- ============================================================================

-- Fast lookup by order
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_order_id
    ON order_items(order_id);

-- Fast lookup by menu item (popularity tracking)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_menu_item_id
    ON order_items(menu_item_id);

-- ============================================================================
-- ORDER STATUS HISTORY TABLE INDEXES
-- ============================================================================

-- Fast lookup of order history
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_status_history_order_id
    ON order_status_history(order_id, created_at DESC);

-- ============================================================================
-- RIDERS TABLE INDEXES
-- ============================================================================

-- Fast lookup by website (business rider management)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_riders_website_id
    ON riders(website_id);

-- Filter by status (active riders)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_riders_status
    ON riders(status);

-- Composite for finding available riders
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_riders_website_status
    ON riders(website_id, status);

-- ============================================================================
-- RIDER LOCATIONS TABLE INDEXES
-- ============================================================================

-- Fast lookup by rider (current location)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rider_locations_rider_id
    ON rider_locations(rider_id, updated_at DESC);

-- Spatial index for location queries (if PostGIS enabled)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rider_locations_geom
--     ON rider_locations USING gist(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326));

-- ============================================================================
-- MENU CATEGORIES TABLE INDEXES
-- ============================================================================

-- Fast lookup by website
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_categories_website_id
    ON menu_categories(website_id);

-- Ordering within website
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_categories_website_order
    ON menu_categories(website_id, display_order);

-- ============================================================================
-- MENU ITEMS TABLE INDEXES
-- ============================================================================

-- Fast lookup by category
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_items_category_id
    ON menu_items(category_id);

-- Filter by availability
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_items_available
    ON menu_items(is_available)
    WHERE is_available = true;

-- Ordering within category
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_menu_items_category_order
    ON menu_items(category_id, display_order);

-- ============================================================================
-- DELIVERY ZONES TABLE INDEXES
-- ============================================================================

-- Fast lookup by website
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_zones_website_id
    ON delivery_zones(website_id);

-- Spatial index for zone containment checks (if using PostGIS)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_delivery_zones_geom
--     ON delivery_zones USING gist(zone_polygon);

-- ============================================================================
-- CHAT TABLES INDEXES
-- ============================================================================

-- Chat conversations by website
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_conversations_website_id
    ON chat_conversations(website_id);

-- Chat conversations by order (order-related chats)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_conversations_order_id
    ON chat_conversations(order_id)
    WHERE order_id IS NOT NULL;

-- Recent conversations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_conversations_updated
    ON chat_conversations(updated_at DESC);

-- Chat messages by conversation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_conversation_id
    ON chat_messages(conversation_id, created_at DESC);

-- Unread messages filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_unread
    ON chat_messages(conversation_id, is_read)
    WHERE is_read = false;

-- ============================================================================
-- ANALYTICS TABLE INDEXES
-- ============================================================================

-- Analytics by website
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_website_id
    ON analytics(website_id);

-- Analytics by date range
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_website_date
    ON analytics(website_id, date DESC);

-- ============================================================================
-- PROFILES TABLE INDEXES
-- ============================================================================

-- Fast lookup by user ID
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_user_id
    ON profiles(id);

-- ============================================================================
-- SUBSCRIPTIONS TABLE INDEXES
-- ============================================================================

-- Subscription by user
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscriptions_user_id
    ON subscriptions(user_id);

-- Active subscriptions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscriptions_status
    ON subscriptions(status)
    WHERE status = 'active';

-- ============================================================================
-- PARTIAL INDEXES FOR COMMON QUERIES
-- ============================================================================

-- Active websites only (most queries filter on this)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_websites_active
    ON websites(user_id, created_at DESC)
    WHERE status = 'PUBLISHED';

-- Pending orders (frequently queried by businesses)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_pending
    ON delivery_orders(website_id, created_at DESC)
    WHERE status IN ('pending', 'confirmed', 'preparing');

-- In-progress orders for riders
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_rider_active
    ON delivery_orders(rider_id, created_at DESC)
    WHERE status IN ('picked_up', 'on_the_way');

-- ============================================================================
-- INDEX MAINTENANCE
-- ============================================================================

-- Run ANALYZE after creating indexes to update statistics
-- ANALYZE websites;
-- ANALYZE delivery_orders;
-- ANALYZE order_items;
-- ANALYZE menu_items;
-- ANALYZE chat_messages;

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Check index usage (run periodically):
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan,
--     idx_tup_read,
--     idx_tup_fetch
-- FROM pg_stat_user_indexes
-- ORDER BY idx_scan DESC;

-- Find unused indexes:
-- SELECT
--     schemaname,
--     tablename,
--     indexname,
--     idx_scan
-- FROM pg_stat_user_indexes
-- WHERE idx_scan = 0
-- AND schemaname NOT IN ('pg_catalog', 'pg_toast')
-- ORDER BY tablename, indexname;

-- Check for missing indexes (tables with seq scans):
-- SELECT
--     schemaname,
--     relname,
--     seq_scan,
--     seq_tup_read,
--     idx_scan,
--     idx_tup_fetch
-- FROM pg_stat_user_tables
-- WHERE seq_scan > 0
-- ORDER BY seq_tup_read DESC;

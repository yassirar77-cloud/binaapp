-- BinaApp Delivery System Migration
-- Run this SQL in Supabase SQL Editor
-- Creates tables for on-demand delivery with real-time tracking

-- =====================================================
-- ENABLE UUID EXTENSION (if not already enabled)
-- =====================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- 1. DELIVERY ZONES (Kawasan Delivery)
-- =====================================================
CREATE TABLE IF NOT EXISTS delivery_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    zone_name VARCHAR(100) NOT NULL,
    zone_polygon JSONB, -- GeoJSON polygon for coverage area
    delivery_fee DECIMAL(10,2) NOT NULL DEFAULT 5.00,
    minimum_order DECIMAL(10,2) DEFAULT 30.00,
    estimated_time_min INTEGER DEFAULT 30, -- minutes
    estimated_time_max INTEGER DEFAULT 45,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 2. MENU CATEGORIES
-- =====================================================
CREATE TABLE IF NOT EXISTS menu_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    icon VARCHAR(50), -- emoji or icon class
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 3. MENU ITEMS
-- =====================================================
CREATE TABLE IF NOT EXISTS menu_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE,
    category_id UUID REFERENCES menu_categories(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    image_url TEXT,
    is_available BOOLEAN DEFAULT true,
    is_popular BOOLEAN DEFAULT false,
    preparation_time INTEGER DEFAULT 15, -- minutes
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 4. MENU ITEM OPTIONS (Add-ons, sizes, etc.)
-- =====================================================
CREATE TABLE IF NOT EXISTS menu_item_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    menu_item_id UUID REFERENCES menu_items(id) ON DELETE CASCADE,
    option_group VARCHAR(100), -- e.g., "Size", "Add-ons", "Spice Level"
    option_name VARCHAR(100) NOT NULL,
    price_modifier DECIMAL(10,2) DEFAULT 0, -- additional price
    is_default BOOLEAN DEFAULT false,
    sort_order INTEGER DEFAULT 0
);

-- =====================================================
-- 5. RIDERS
-- =====================================================
CREATE TABLE IF NOT EXISTS riders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES websites(id), -- Can be null for shared riders

    -- Personal Info
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(200),
    photo_url TEXT,

    -- Vehicle Info
    vehicle_type VARCHAR(50), -- 'motorcycle', 'bicycle', 'car'
    vehicle_plate VARCHAR(20),
    vehicle_model VARCHAR(100),

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_online BOOLEAN DEFAULT false,
    current_latitude DECIMAL(10,8),
    current_longitude DECIMAL(11,8),
    last_location_update TIMESTAMPTZ,

    -- Stats
    total_deliveries INTEGER DEFAULT 0,
    rating DECIMAL(3,2) DEFAULT 5.00,
    total_ratings INTEGER DEFAULT 0,

    -- Auth
    password_hash TEXT,
    auth_token TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 6. DELIVERY ORDERS
-- =====================================================
CREATE TABLE IF NOT EXISTS delivery_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(20) UNIQUE NOT NULL, -- e.g., "BNA-12345"
    website_id UUID REFERENCES websites(id),

    -- Customer Info
    customer_name VARCHAR(200) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    customer_email VARCHAR(200),

    -- Delivery Address
    delivery_address TEXT NOT NULL,
    delivery_latitude DECIMAL(10,8),
    delivery_longitude DECIMAL(11,8),
    delivery_notes TEXT,

    -- Zone & Fee
    delivery_zone_id UUID REFERENCES delivery_zones(id),
    delivery_fee DECIMAL(10,2) NOT NULL,

    -- Order Amounts
    subtotal DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,

    -- Payment
    payment_method VARCHAR(50) NOT NULL, -- 'cod', 'online', 'ewallet'
    payment_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'paid', 'failed', 'refunded'
    payment_reference VARCHAR(100),

    -- Order Status
    status VARCHAR(50) DEFAULT 'pending',
    -- Status flow: pending → confirmed → preparing → ready → picked_up → delivering → delivered → completed
    -- Or: cancelled, rejected

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    preparing_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    picked_up_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    -- Rider
    rider_id UUID REFERENCES riders(id),

    -- Estimated times
    estimated_prep_time INTEGER, -- minutes
    estimated_delivery_time INTEGER,
    actual_delivery_time INTEGER
);

-- =====================================================
-- 7. ORDER ITEMS
-- =====================================================
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES delivery_orders(id) ON DELETE CASCADE,
    menu_item_id UUID REFERENCES menu_items(id),
    item_name VARCHAR(200) NOT NULL, -- Store name at time of order
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    options JSONB, -- Selected options
    notes TEXT
);

-- =====================================================
-- 8. RIDER LOCATION HISTORY (for tracking)
-- =====================================================
CREATE TABLE IF NOT EXISTS rider_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rider_id UUID REFERENCES riders(id) ON DELETE CASCADE,
    order_id UUID REFERENCES delivery_orders(id),
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 9. ORDER STATUS HISTORY
-- =====================================================
CREATE TABLE IF NOT EXISTS order_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES delivery_orders(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    notes TEXT,
    updated_by VARCHAR(50), -- 'system', 'business', 'rider', 'customer'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- 10. DELIVERY SETTINGS (per business)
-- =====================================================
CREATE TABLE IF NOT EXISTS delivery_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES websites(id) ON DELETE CASCADE UNIQUE,

    -- Operating Hours
    delivery_hours JSONB, -- {"mon": {"open": "09:00", "close": "22:00"}, ...}

    -- Order Settings
    minimum_order DECIMAL(10,2) DEFAULT 30.00,
    max_delivery_distance DECIMAL(10,2) DEFAULT 10.00, -- km
    auto_accept_orders BOOLEAN DEFAULT false,

    -- Notifications
    notify_whatsapp BOOLEAN DEFAULT true,
    notify_email BOOLEAN DEFAULT false,
    notify_sound BOOLEAN DEFAULT true,

    -- WhatsApp
    whatsapp_number VARCHAR(20),

    -- Payment Methods
    accept_cod BOOLEAN DEFAULT true,
    accept_online BOOLEAN DEFAULT false,
    accept_ewallet BOOLEAN DEFAULT false,

    -- Rider Settings
    use_own_riders BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_delivery_zones_website ON delivery_zones(website_id);
CREATE INDEX IF NOT EXISTS idx_menu_categories_website ON menu_categories(website_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_website ON menu_items(website_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_category ON menu_items(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_website ON delivery_orders(website_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON delivery_orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON delivery_orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_rider ON delivery_orders(rider_id);
CREATE INDEX IF NOT EXISTS idx_orders_number ON delivery_orders(order_number);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_rider_locations_rider ON rider_locations(rider_id);
CREATE INDEX IF NOT EXISTS idx_rider_locations_order ON rider_locations(order_id);
CREATE INDEX IF NOT EXISTS idx_riders_online ON riders(is_online) WHERE is_online = true;

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE delivery_zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_item_options ENABLE ROW LEVEL SECURITY;
ALTER TABLE riders ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE rider_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_settings ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS POLICIES - Business Owner Access
-- =====================================================

-- Delivery Zones
DROP POLICY IF EXISTS "Users can view own delivery zones" ON delivery_zones;
CREATE POLICY "Users can view own delivery zones" ON delivery_zones
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can manage own delivery zones" ON delivery_zones;
CREATE POLICY "Users can manage own delivery zones" ON delivery_zones
    FOR ALL USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- Menu Categories
DROP POLICY IF EXISTS "Users can view own menu categories" ON menu_categories;
CREATE POLICY "Users can view own menu categories" ON menu_categories
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can manage own menu categories" ON menu_categories;
CREATE POLICY "Users can manage own menu categories" ON menu_categories
    FOR ALL USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- Menu Items
DROP POLICY IF EXISTS "Users can view own menu items" ON menu_items;
CREATE POLICY "Users can view own menu items" ON menu_items
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can manage own menu items" ON menu_items;
CREATE POLICY "Users can manage own menu items" ON menu_items
    FOR ALL USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- Delivery Orders
DROP POLICY IF EXISTS "Users can view own orders" ON delivery_orders;
CREATE POLICY "Users can view own orders" ON delivery_orders
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can manage own orders" ON delivery_orders;
CREATE POLICY "Users can manage own orders" ON delivery_orders
    FOR ALL USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- Riders
DROP POLICY IF EXISTS "Users can view own riders" ON riders;
CREATE POLICY "Users can view own riders" ON riders
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
        OR website_id IS NULL  -- Shared riders
    );

DROP POLICY IF EXISTS "Users can manage own riders" ON riders;
CREATE POLICY "Users can manage own riders" ON riders
    FOR ALL USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
    );

-- =====================================================
-- RLS POLICIES - Public Access (for customer ordering)
-- =====================================================

-- Public can view active delivery zones
DROP POLICY IF EXISTS "Public can view active zones" ON delivery_zones;
CREATE POLICY "Public can view active zones" ON delivery_zones
    FOR SELECT USING (is_active = true);

-- Public can view menu categories
DROP POLICY IF EXISTS "Public can view menu categories" ON menu_categories;
CREATE POLICY "Public can view menu categories" ON menu_categories
    FOR SELECT USING (is_active = true);

-- Public can view available menu items
DROP POLICY IF EXISTS "Public can view menu items" ON menu_items;
CREATE POLICY "Public can view menu items" ON menu_items
    FOR SELECT USING (is_available = true);

-- Public can create orders (anonymous ordering)
DROP POLICY IF EXISTS "Anyone can create orders" ON delivery_orders;
CREATE POLICY "Anyone can create orders" ON delivery_orders
    FOR INSERT WITH CHECK (true);

-- Public can view their own order by order_number (for tracking)
DROP POLICY IF EXISTS "Anyone can track orders by number" ON delivery_orders;
CREATE POLICY "Anyone can track orders by number" ON delivery_orders
    FOR SELECT USING (true);  -- We'll handle filtering in application layer

-- Public can view order items for tracking
DROP POLICY IF EXISTS "Anyone can view order items" ON order_items;
CREATE POLICY "Anyone can view order items" ON order_items
    FOR SELECT USING (true);

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================
GRANT ALL ON delivery_zones TO service_role;
GRANT ALL ON menu_categories TO service_role;
GRANT ALL ON menu_items TO service_role;
GRANT ALL ON menu_item_options TO service_role;
GRANT ALL ON riders TO service_role;
GRANT ALL ON delivery_orders TO service_role;
GRANT ALL ON order_items TO service_role;
GRANT ALL ON rider_locations TO service_role;
GRANT ALL ON order_status_history TO service_role;
GRANT ALL ON delivery_settings TO service_role;

GRANT ALL ON delivery_zones TO authenticated;
GRANT ALL ON menu_categories TO authenticated;
GRANT ALL ON menu_items TO authenticated;
GRANT ALL ON menu_item_options TO authenticated;
GRANT ALL ON riders TO authenticated;
GRANT ALL ON delivery_orders TO authenticated;
GRANT ALL ON order_items TO authenticated;
GRANT ALL ON rider_locations TO authenticated;
GRANT ALL ON order_status_history TO authenticated;
GRANT ALL ON delivery_settings TO authenticated;

GRANT SELECT ON delivery_zones TO anon;
GRANT SELECT ON menu_categories TO anon;
GRANT SELECT ON menu_items TO anon;
GRANT SELECT ON menu_item_options TO anon;
GRANT INSERT ON delivery_orders TO anon;
GRANT SELECT ON delivery_orders TO anon;
GRANT INSERT ON order_items TO anon;
GRANT SELECT ON order_items TO anon;
GRANT INSERT ON order_status_history TO anon;
GRANT SELECT ON order_status_history TO anon;
GRANT SELECT ON delivery_settings TO anon;

-- =====================================================
-- ENABLE REAL-TIME SUBSCRIPTIONS
-- =====================================================
-- Enable real-time for order tracking
ALTER PUBLICATION supabase_realtime ADD TABLE delivery_orders;
ALTER PUBLICATION supabase_realtime ADD TABLE rider_locations;
ALTER PUBLICATION supabase_realtime ADD TABLE order_status_history;

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_delivery_zones_updated_at ON delivery_zones;
CREATE TRIGGER update_delivery_zones_updated_at
    BEFORE UPDATE ON delivery_zones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_menu_items_updated_at ON menu_items;
CREATE TRIGGER update_menu_items_updated_at
    BEFORE UPDATE ON menu_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_delivery_settings_updated_at ON delivery_settings;
CREATE TRIGGER update_delivery_settings_updated_at
    BEFORE UPDATE ON delivery_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate order number
CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TEXT AS $$
DECLARE
    new_number TEXT;
    counter INTEGER;
BEGIN
    -- Get count of orders today
    SELECT COUNT(*) INTO counter
    FROM delivery_orders
    WHERE DATE(created_at) = CURRENT_DATE;

    -- Generate order number: BNA-YYYYMMDD-XXXX
    new_number := 'BNA-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD((counter + 1)::TEXT, 4, '0');

    RETURN new_number;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-generate order number
CREATE OR REPLACE FUNCTION set_order_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.order_number IS NULL OR NEW.order_number = '' THEN
        NEW.order_number := generate_order_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_order_number_trigger ON delivery_orders;
CREATE TRIGGER set_order_number_trigger
    BEFORE INSERT ON delivery_orders
    FOR EACH ROW EXECUTE FUNCTION set_order_number();

-- Function to log status changes
CREATE OR REPLACE FUNCTION log_order_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE' AND OLD.status != NEW.status) THEN
        INSERT INTO order_status_history (order_id, status, updated_by, notes)
        VALUES (NEW.id, NEW.status, 'system', 'Status changed from ' || OLD.status || ' to ' || NEW.status);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS log_order_status_trigger ON delivery_orders;
CREATE TRIGGER log_order_status_trigger
    AFTER UPDATE ON delivery_orders
    FOR EACH ROW EXECUTE FUNCTION log_order_status_change();

-- =====================================================
-- DONE! BinaApp Delivery System is ready.
-- =====================================================

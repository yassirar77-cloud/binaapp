-- ==========================================================================
-- BINAAPP COMPLETE DATABASE SCHEMA
-- ==========================================================================
-- This file contains ALL tables, functions, triggers, and RLS policies
-- for the BinaApp platform.
--
-- IMPORTANT: Run these migrations in ORDER:
-- 1. This file (core schema)
-- 2. Any additional migrations in backend/migrations/ folder
--
-- Generated: 2026-01-11
-- Purpose: Complete backup for account transition
-- ==========================================================================

-- Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "postgis";  -- For geolocation (optional)

-- ==========================================================================
-- SECTION 1: USER MANAGEMENT
-- ==========================================================================

-- ===================================
-- Profiles Table (extends auth.users)
-- ===================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    full_name TEXT,
    business_name TEXT,
    avatar_url TEXT,
    phone TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policies for Profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

-- ===================================
-- Subscriptions Table
-- ===================================
CREATE TABLE IF NOT EXISTS public.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',  -- 'free', 'basic', 'pro', 'enterprise'
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'cancelled', 'expired', 'past_due'
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscription"
    ON public.subscriptions FOR SELECT
    USING (auth.uid() = user_id);

-- ==========================================================================
-- SECTION 2: WEBSITES
-- ==========================================================================

-- ===================================
-- Websites Table
-- ===================================
CREATE TABLE IF NOT EXISTS public.websites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    -- Business Info
    business_name TEXT NOT NULL,
    business_type TEXT,  -- 'restaurant', 'salon', 'retail', 'services'
    subdomain TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft',  -- 'draft', 'generating', 'published', 'failed'
    language TEXT DEFAULT 'ms',  -- 'ms' (Bahasa), 'en' (English)

    -- Content
    html_content TEXT,
    meta_title TEXT,
    meta_description TEXT,
    sections TEXT[],
    integrations TEXT[],

    -- Integration Settings
    include_whatsapp BOOLEAN DEFAULT false,
    whatsapp_number TEXT,
    include_maps BOOLEAN DEFAULT false,
    location_address TEXT,
    include_ecommerce BOOLEAN DEFAULT false,
    contact_email TEXT,

    -- Publishing
    published_at TIMESTAMPTZ,
    public_url TEXT,  -- https://subdomain.binaapp.my
    preview_url TEXT,

    -- Metadata
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_websites_user_id ON public.websites(user_id);
CREATE INDEX idx_websites_subdomain ON public.websites(subdomain);
CREATE INDEX idx_websites_status ON public.websites(status);
CREATE INDEX idx_websites_created ON public.websites(created_at DESC);

-- RLS Policies
ALTER TABLE public.websites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own websites"
    ON public.websites FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own websites"
    ON public.websites FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own websites"
    ON public.websites FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own websites"
    ON public.websites FOR DELETE
    USING (auth.uid() = user_id);

-- ==========================================================================
-- SECTION 3: ANALYTICS
-- ==========================================================================

-- ===================================
-- Analytics Table
-- ===================================
CREATE TABLE IF NOT EXISTS public.analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,

    -- Metrics
    total_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    whatsapp_clicks INTEGER DEFAULT 0,
    form_submissions INTEGER DEFAULT 0,
    cart_interactions INTEGER DEFAULT 0,

    -- Timestamps
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(website_id)
);

CREATE INDEX idx_analytics_website_id ON public.analytics(website_id);

ALTER TABLE public.analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view analytics for own websites"
    ON public.analytics FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.websites
            WHERE websites.id = analytics.website_id
            AND websites.user_id = auth.uid()
        )
    );

-- ==========================================================================
-- SECTION 4: TEMPLATES
-- ==========================================================================

-- ===================================
-- Templates Table
-- ===================================
CREATE TABLE IF NOT EXISTS public.templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'restaurant', 'retail', 'services', 'salon'
    description TEXT,
    html_template TEXT NOT NULL,
    thumbnail_url TEXT,
    preview_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON public.templates(category);
CREATE INDEX idx_templates_active ON public.templates(is_active);

ALTER TABLE public.templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Templates are viewable by everyone"
    ON public.templates FOR SELECT
    USING (is_active = true);

-- ==========================================================================
-- SECTION 5: MENU MANAGEMENT
-- ==========================================================================

-- ===================================
-- Menu Categories
-- ===================================
CREATE TABLE IF NOT EXISTS public.menu_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,  -- "Nasi", "Mee", "Minuman"
    name_en TEXT,  -- English translation
    slug TEXT NOT NULL,
    icon TEXT,  -- Emoji or icon class
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(website_id, slug)
);

CREATE INDEX idx_menu_categories_website ON public.menu_categories(website_id);
CREATE INDEX idx_menu_categories_sort ON public.menu_categories(website_id, sort_order);

ALTER TABLE public.menu_categories ENABLE ROW LEVEL SECURITY;

-- Owner policies
CREATE POLICY "Users can view own menu categories"
    ON public.menu_categories FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can manage own menu categories"
    ON public.menu_categories FOR ALL
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

-- Public policies
CREATE POLICY "Public can view menu categories"
    ON public.menu_categories FOR SELECT
    USING (is_active = true);

-- ===================================
-- Menu Items
-- ===================================
CREATE TABLE IF NOT EXISTS public.menu_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,
    category_id UUID REFERENCES public.menu_categories(id) ON DELETE SET NULL,

    -- Item Info
    name TEXT NOT NULL,  -- "Nasi Lemak", "Teh Tarik"
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    image_url TEXT,  -- Cloudinary URL

    -- Availability
    is_available BOOLEAN DEFAULT true,
    is_popular BOOLEAN DEFAULT false,

    -- Timing
    preparation_time INTEGER DEFAULT 15,  -- minutes

    -- Sorting
    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menu_items_website ON public.menu_items(website_id);
CREATE INDEX idx_menu_items_category ON public.menu_items(category_id);
CREATE INDEX idx_menu_items_available ON public.menu_items(website_id, is_available);
CREATE INDEX idx_menu_items_sort ON public.menu_items(website_id, category_id, sort_order);

ALTER TABLE public.menu_items ENABLE ROW LEVEL SECURITY;

-- Owner policies
CREATE POLICY "Users can view own menu items"
    ON public.menu_items FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can manage own menu items"
    ON public.menu_items FOR ALL
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

-- Public policies
CREATE POLICY "Public can view available menu items"
    ON public.menu_items FOR SELECT
    USING (is_available = true);

-- ===================================
-- Menu Item Options (add-ons, sizes)
-- ===================================
CREATE TABLE IF NOT EXISTS public.menu_item_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    menu_item_id UUID REFERENCES public.menu_items(id) ON DELETE CASCADE NOT NULL,
    option_group TEXT,  -- "Size", "Add-ons", "Spice Level"
    option_name TEXT NOT NULL,
    price_modifier DECIMAL(10,2) DEFAULT 0,  -- Additional cost
    is_default BOOLEAN DEFAULT false,
    sort_order INTEGER DEFAULT 0
);

CREATE INDEX idx_menu_item_options_item ON public.menu_item_options(menu_item_id);

ALTER TABLE public.menu_item_options ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view menu item options"
    ON public.menu_item_options FOR SELECT
    USING (true);

CREATE POLICY "Users can manage own menu item options"
    ON public.menu_item_options FOR ALL
    USING (
        menu_item_id IN (
            SELECT id FROM public.menu_items
            WHERE website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
        )
    );

-- ==========================================================================
-- SECTION 6: DELIVERY SYSTEM
-- ==========================================================================

-- ===================================
-- Delivery Zones
-- ===================================
CREATE TABLE IF NOT EXISTS public.delivery_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,

    -- Zone Info
    zone_name TEXT NOT NULL,  -- "Shah Alam", "Petaling Jaya"
    zone_polygon JSONB,  -- GeoJSON polygon for coverage area

    -- Pricing
    delivery_fee DECIMAL(10,2) NOT NULL DEFAULT 5.00,
    minimum_order DECIMAL(10,2) DEFAULT 30.00,

    -- Timing
    estimated_time_min INTEGER DEFAULT 30,  -- minutes
    estimated_time_max INTEGER DEFAULT 45,

    -- Status
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_delivery_zones_website ON public.delivery_zones(website_id);
CREATE INDEX idx_delivery_zones_active ON public.delivery_zones(website_id, is_active);

ALTER TABLE public.delivery_zones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own delivery zones"
    ON public.delivery_zones FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can manage own delivery zones"
    ON public.delivery_zones FOR ALL
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Public can view active zones"
    ON public.delivery_zones FOR SELECT
    USING (is_active = true);

-- ===================================
-- Riders
-- ===================================
CREATE TABLE IF NOT EXISTS public.riders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES public.websites(id) ON DELETE SET NULL,  -- Null for shared riders
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,  -- Optional: if rider has account

    -- Personal Info
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    photo_url TEXT,

    -- Vehicle Info
    vehicle_type TEXT,  -- 'motorcycle', 'bicycle', 'car'
    vehicle_plate TEXT,
    vehicle_model TEXT,

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_online BOOLEAN DEFAULT false,

    -- Location (real-time GPS)
    current_latitude DECIMAL(10,8),
    current_longitude DECIMAL(11,8),
    location_updated_at TIMESTAMPTZ,

    -- Stats
    total_deliveries INTEGER DEFAULT 0,
    rating DECIMAL(3,2) DEFAULT 5.00,
    total_ratings INTEGER DEFAULT 0,

    -- Auth (if using separate rider login)
    password_hash TEXT,
    auth_token TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_riders_website ON public.riders(website_id);
CREATE INDEX idx_riders_online ON public.riders(is_online) WHERE is_online = true;
CREATE INDEX idx_riders_phone ON public.riders(phone);

ALTER TABLE public.riders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own riders"
    ON public.riders FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
        OR website_id IS NULL  -- Shared riders
    );

CREATE POLICY "Users can manage own riders"
    ON public.riders FOR ALL
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

-- ===================================
-- Delivery Orders
-- ===================================
CREATE TABLE IF NOT EXISTS public.delivery_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number TEXT UNIQUE NOT NULL,  -- Auto-generated: ORD-20250111-001
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,

    -- Customer Info
    customer_id UUID,  -- Optional: if customer has account
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_email TEXT,

    -- Delivery Address
    delivery_address TEXT NOT NULL,
    delivery_latitude DECIMAL(10,8),
    delivery_longitude DECIMAL(11,8),
    delivery_notes TEXT,

    -- Zone & Fee
    delivery_zone_id UUID REFERENCES public.delivery_zones(id),
    delivery_zone TEXT,  -- Zone name stored for historical reference
    delivery_fee DECIMAL(10,2) NOT NULL,

    -- Order Amounts
    subtotal DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,

    -- Payment
    payment_method TEXT NOT NULL,  -- 'cod', 'online', 'ewallet'
    payment_status TEXT DEFAULT 'pending',  -- 'pending', 'paid', 'failed', 'refunded'
    payment_reference TEXT,

    -- Order Status
    status TEXT DEFAULT 'pending',
    /* Status flow:
       pending → confirmed → preparing → ready → picked_up → delivering → delivered → completed
       OR: cancelled, rejected
    */

    -- Timestamps for each status
    created_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    preparing_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    picked_up_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    -- Rider Assignment
    rider_id UUID REFERENCES public.riders(id),
    assigned_at TIMESTAMPTZ,

    -- Estimated Times
    estimated_prep_time INTEGER,  -- minutes
    estimated_delivery_time INTEGER,
    actual_delivery_time INTEGER
);

CREATE INDEX idx_orders_website ON public.delivery_orders(website_id);
CREATE INDEX idx_orders_status ON public.delivery_orders(status);
CREATE INDEX idx_orders_created ON public.delivery_orders(created_at DESC);
CREATE INDEX idx_orders_rider ON public.delivery_orders(rider_id);
CREATE INDEX idx_orders_number ON public.delivery_orders(order_number);
CREATE INDEX idx_orders_customer ON public.delivery_orders(customer_phone);

ALTER TABLE public.delivery_orders ENABLE ROW LEVEL SECURITY;

-- Owner policies
CREATE POLICY "Users can view own orders"
    ON public.delivery_orders FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can update own orders"
    ON public.delivery_orders FOR UPDATE
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

-- Public policies (for customer ordering)
CREATE POLICY "Anyone can create orders"
    ON public.delivery_orders FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Anyone can track orders"
    ON public.delivery_orders FOR SELECT
    USING (true);  -- Filtered by order_number in application layer

-- ===================================
-- Order Items
-- ===================================
CREATE TABLE IF NOT EXISTS public.order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES public.delivery_orders(id) ON DELETE CASCADE NOT NULL,
    menu_item_id UUID REFERENCES public.menu_items(id),

    -- Store item details at time of order
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,

    -- Selected options
    options JSONB,  -- [{"group": "Size", "option": "Large", "price": 2.00}]
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_order_items_order ON public.order_items(order_id);
CREATE INDEX idx_order_items_menu_item ON public.order_items(menu_item_id);

ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view order items"
    ON public.order_items FOR SELECT
    USING (true);

CREATE POLICY "Anyone can create order items"
    ON public.order_items FOR INSERT
    WITH CHECK (true);

-- ===================================
-- Rider Location History
-- ===================================
CREATE TABLE IF NOT EXISTS public.rider_locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rider_id UUID REFERENCES public.riders(id) ON DELETE CASCADE NOT NULL,
    order_id UUID REFERENCES public.delivery_orders(id),

    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    accuracy DECIMAL(10,2),  -- meters

    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rider_locations_rider ON public.rider_locations(rider_id);
CREATE INDEX idx_rider_locations_order ON public.rider_locations(order_id);
CREATE INDEX idx_rider_locations_time ON public.rider_locations(recorded_at DESC);

ALTER TABLE public.rider_locations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view rider locations for own orders"
    ON public.rider_locations FOR SELECT
    USING (
        order_id IN (
            SELECT id FROM public.delivery_orders
            WHERE website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
        )
    );

-- ===================================
-- Order Status History
-- ===================================
CREATE TABLE IF NOT EXISTS public.order_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES public.delivery_orders(id) ON DELETE CASCADE NOT NULL,

    status TEXT NOT NULL,
    notes TEXT,
    updated_by TEXT,  -- 'system', 'business', 'rider', 'customer'

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_order_status_history_order ON public.order_status_history(order_id);
CREATE INDEX idx_order_status_history_time ON public.order_status_history(created_at DESC);

ALTER TABLE public.order_status_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view order status history for own orders"
    ON public.order_status_history FOR SELECT
    USING (
        order_id IN (
            SELECT id FROM public.delivery_orders
            WHERE website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
        )
    );

-- ===================================
-- Delivery Settings
-- ===================================
CREATE TABLE IF NOT EXISTS public.delivery_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE UNIQUE NOT NULL,

    -- Operating Hours
    delivery_hours JSONB,  -- {"mon": {"open": "09:00", "close": "22:00"}, ...}

    -- Order Settings
    minimum_order DECIMAL(10,2) DEFAULT 30.00,
    max_delivery_distance DECIMAL(10,2) DEFAULT 10.00,  -- km
    auto_accept_orders BOOLEAN DEFAULT false,

    -- Notifications
    notify_whatsapp BOOLEAN DEFAULT true,
    notify_email BOOLEAN DEFAULT false,
    notify_sound BOOLEAN DEFAULT true,

    -- WhatsApp
    whatsapp_number TEXT,

    -- Payment Methods
    accept_cod BOOLEAN DEFAULT true,
    accept_online BOOLEAN DEFAULT false,
    accept_ewallet BOOLEAN DEFAULT false,

    -- Rider Settings
    use_own_riders BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.delivery_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own delivery settings"
    ON public.delivery_settings FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can manage own delivery settings"
    ON public.delivery_settings FOR ALL
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

-- ==========================================================================
-- SECTION 7: CHAT SYSTEM
-- ==========================================================================

-- ===================================
-- Chat Conversations
-- ===================================
CREATE TABLE IF NOT EXISTS public.chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES public.delivery_orders(id) ON DELETE SET NULL,
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,

    -- Customer Info
    customer_id TEXT NOT NULL,  -- Phone or generated ID
    customer_name TEXT,
    customer_phone TEXT,

    -- Status
    status TEXT DEFAULT 'active',  -- 'active', 'closed', 'archived'

    -- Unread Counts
    unread_owner INTEGER DEFAULT 0,
    unread_customer INTEGER DEFAULT 0,
    unread_rider INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_conversations_order ON public.chat_conversations(order_id);
CREATE INDEX idx_chat_conversations_website ON public.chat_conversations(website_id);
CREATE INDEX idx_chat_conversations_customer ON public.chat_conversations(customer_id);
CREATE INDEX idx_chat_conversations_status ON public.chat_conversations(status);
CREATE INDEX idx_chat_conversations_updated ON public.chat_conversations(updated_at DESC);

ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own conversations"
    ON public.chat_conversations FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Users can manage own conversations"
    ON public.chat_conversations FOR ALL
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

CREATE POLICY "Anyone can create conversations"
    ON public.chat_conversations FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Anyone can view conversations"
    ON public.chat_conversations FOR SELECT
    USING (true);  -- Filtered in application layer

-- ===================================
-- Chat Messages
-- ===================================
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES public.chat_conversations(id) ON DELETE CASCADE NOT NULL,

    -- Sender Info
    sender_type TEXT NOT NULL,  -- 'customer', 'owner', 'rider', 'system'
    sender_id TEXT,
    sender_name TEXT,

    -- Message Content
    message_type TEXT DEFAULT 'text',  -- 'text', 'image', 'location', 'payment', 'status', 'voice'
    content TEXT,
    media_url TEXT,  -- Cloudinary URL for images/voice
    metadata JSONB,  -- Location coords, payment info, etc.

    -- Read Status
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    read_by JSONB DEFAULT '[]'::jsonb,  -- Array of user types who read

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_conversation ON public.chat_messages(conversation_id);
CREATE INDEX idx_chat_messages_created ON public.chat_messages(created_at DESC);
CREATE INDEX idx_chat_messages_sender ON public.chat_messages(sender_type, sender_id);
CREATE INDEX idx_chat_messages_type ON public.chat_messages(message_type);

ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view messages"
    ON public.chat_messages FOR SELECT
    USING (true);

CREATE POLICY "Anyone can insert messages"
    ON public.chat_messages FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Anyone can update messages"
    ON public.chat_messages FOR UPDATE
    USING (true);

-- ===================================
-- Chat Participants
-- ===================================
CREATE TABLE IF NOT EXISTS public.chat_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES public.chat_conversations(id) ON DELETE CASCADE NOT NULL,

    -- User Info
    user_type TEXT NOT NULL,  -- 'customer', 'owner', 'rider'
    user_id TEXT,
    user_name TEXT,

    -- Online Status
    is_online BOOLEAN DEFAULT false,
    last_seen TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(conversation_id, user_type, user_id)
);

CREATE INDEX idx_chat_participants_conversation ON public.chat_participants(conversation_id);
CREATE INDEX idx_chat_participants_user ON public.chat_participants(user_type, user_id);

ALTER TABLE public.chat_participants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view participants"
    ON public.chat_participants FOR SELECT
    USING (true);

CREATE POLICY "Anyone can manage participants"
    ON public.chat_participants FOR ALL
    USING (true);

-- ==========================================================================
-- SECTION 8: FUNCTIONS & TRIGGERS
-- ==========================================================================

-- ===================================
-- Function: Update updated_at Timestamp
-- ===================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON public.subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_websites_updated_at
    BEFORE UPDATE ON public.websites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_menu_categories_updated_at
    BEFORE UPDATE ON public.menu_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_menu_items_updated_at
    BEFORE UPDATE ON public.menu_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_delivery_zones_updated_at
    BEFORE UPDATE ON public.delivery_zones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_delivery_settings_updated_at
    BEFORE UPDATE ON public.delivery_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_riders_updated_at
    BEFORE UPDATE ON public.riders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_conversations_updated_at
    BEFORE UPDATE ON public.chat_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===================================
-- Function: Create Profile on User Signup
-- ===================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Create profile
    INSERT INTO public.profiles (id, full_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'full_name');

    -- Create free subscription
    INSERT INTO public.subscriptions (user_id, tier, status)
    VALUES (NEW.id, 'free', 'active');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ===================================
-- Function: Increment Website Views
-- ===================================
CREATE OR REPLACE FUNCTION increment_views(website_id UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO public.analytics (website_id, total_views, unique_visitors)
    VALUES (website_id, 1, 1)
    ON CONFLICT (website_id)
    DO UPDATE SET
        total_views = analytics.total_views + 1,
        last_updated = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===================================
-- Function: Generate Order Number
-- ===================================
CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TEXT AS $$
DECLARE
    new_number TEXT;
    counter INTEGER;
BEGIN
    -- Get count of orders today
    SELECT COUNT(*) INTO counter
    FROM public.delivery_orders
    WHERE DATE(created_at) = CURRENT_DATE;

    -- Generate: ORD-20250111-0001
    new_number := 'ORD-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD((counter + 1)::TEXT, 4, '0');

    RETURN new_number;
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- Trigger: Auto-generate Order Number
-- ===================================
CREATE OR REPLACE FUNCTION set_order_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.order_number IS NULL OR NEW.order_number = '' THEN
        NEW.order_number := generate_order_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_order_number_trigger
    BEFORE INSERT ON public.delivery_orders
    FOR EACH ROW EXECUTE FUNCTION set_order_number();

-- ===================================
-- Function: Log Order Status Changes
-- ===================================
CREATE OR REPLACE FUNCTION log_order_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status) THEN
        INSERT INTO public.order_status_history (order_id, status, updated_by, notes)
        VALUES (
            NEW.id,
            NEW.status,
            'system',
            'Status changed from ' || COALESCE(OLD.status, 'null') || ' to ' || NEW.status
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_order_status_trigger
    AFTER UPDATE ON public.delivery_orders
    FOR EACH ROW EXECUTE FUNCTION log_order_status_change();

-- ===================================
-- Function: Update Conversation on New Message
-- ===================================
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    -- Update conversation timestamp
    UPDATE public.chat_conversations
    SET updated_at = NOW()
    WHERE id = NEW.conversation_id;

    -- Update unread counts based on sender type
    IF NEW.sender_type = 'customer' THEN
        UPDATE public.chat_conversations
        SET unread_owner = unread_owner + 1,
            unread_rider = unread_rider + 1
        WHERE id = NEW.conversation_id;
    ELSIF NEW.sender_type = 'owner' THEN
        UPDATE public.chat_conversations
        SET unread_customer = unread_customer + 1,
            unread_rider = unread_rider + 1
        WHERE id = NEW.conversation_id;
    ELSIF NEW.sender_type = 'rider' THEN
        UPDATE public.chat_conversations
        SET unread_customer = unread_customer + 1,
            unread_owner = unread_owner + 1
        WHERE id = NEW.conversation_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_conversation_on_message_trigger
    AFTER INSERT ON public.chat_messages
    FOR EACH ROW EXECUTE FUNCTION update_conversation_on_message();

-- ==========================================================================
-- SECTION 9: PERMISSIONS
-- ==========================================================================

-- Grant service role full access
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Grant authenticated users access
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant anon users limited access (for public ordering)
GRANT SELECT ON public.websites TO anon;
GRANT SELECT ON public.menu_categories TO anon;
GRANT SELECT ON public.menu_items TO anon;
GRANT SELECT ON public.menu_item_options TO anon;
GRANT SELECT ON public.delivery_zones TO anon;
GRANT SELECT, INSERT ON public.delivery_orders TO anon;
GRANT SELECT, INSERT ON public.order_items TO anon;
GRANT SELECT, INSERT ON public.order_status_history TO anon;
GRANT SELECT ON public.delivery_settings TO anon;
GRANT SELECT, INSERT, UPDATE ON public.chat_conversations TO anon;
GRANT SELECT, INSERT, UPDATE ON public.chat_messages TO anon;
GRANT SELECT, INSERT, UPDATE ON public.chat_participants TO anon;

-- ==========================================================================
-- SECTION 10: REALTIME SUBSCRIPTIONS
-- ==========================================================================

-- Enable realtime for order tracking and chat
ALTER PUBLICATION supabase_realtime ADD TABLE public.delivery_orders;
ALTER PUBLICATION supabase_realtime ADD TABLE public.order_status_history;
ALTER PUBLICATION supabase_realtime ADD TABLE public.riders;
ALTER PUBLICATION supabase_realtime ADD TABLE public.rider_locations;
ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_conversations;
ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE public.chat_participants;

-- ==========================================================================
-- SECTION 11: SAMPLE DATA (Optional)
-- ==========================================================================

-- Sample templates
INSERT INTO public.templates (name, category, description, html_template, is_active) VALUES
('Restaurant Template', 'restaurant', 'Modern restaurant template with menu', '<!DOCTYPE html><html><head><title>Restaurant</title></head><body><h1>My Restaurant</h1></body></html>', true),
('Retail Template', 'retail', 'Clean retail store template', '<!DOCTYPE html><html><head><title>Store</title></head><body><h1>My Store</h1></body></html>', true),
('Salon Template', 'salon', 'Elegant salon template', '<!DOCTYPE html><html><head><title>Salon</title></head><body><h1>My Salon</h1></body></html>', true)
ON CONFLICT DO NOTHING;

-- ==========================================================================
-- COMMENTS & DOCUMENTATION
-- ==========================================================================

COMMENT ON TABLE public.profiles IS 'User profiles extending Supabase auth.users';
COMMENT ON TABLE public.subscriptions IS 'User subscription tiers (free, basic, pro)';
COMMENT ON TABLE public.websites IS 'User-created websites with AI-generated HTML';
COMMENT ON TABLE public.analytics IS 'Website analytics (views, clicks, submissions)';
COMMENT ON TABLE public.menu_categories IS 'Menu categories for restaurant websites';
COMMENT ON TABLE public.menu_items IS 'Menu items with pricing and availability';
COMMENT ON TABLE public.delivery_zones IS 'Delivery zones with fees and estimated times';
COMMENT ON TABLE public.riders IS 'Delivery riders with real-time GPS tracking';
COMMENT ON TABLE public.delivery_orders IS 'Customer orders with delivery tracking';
COMMENT ON TABLE public.order_items IS 'Line items for each order';
COMMENT ON TABLE public.chat_conversations IS 'Chat conversations for orders';
COMMENT ON TABLE public.chat_messages IS 'Chat messages with media support';

-- ==========================================================================
-- SCHEMA COMPLETE!
-- ==========================================================================

-- Verify tables created
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verify RLS enabled
SELECT
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND rowsecurity = true
ORDER BY tablename;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ BinaApp database schema created successfully!';
    RAISE NOTICE 'Total tables created: %', (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public');
    RAISE NOTICE 'RLS enabled on: % tables', (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true);
END $$;

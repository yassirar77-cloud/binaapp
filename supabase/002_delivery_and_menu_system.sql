-- Migration: Delivery and Menu Management System
-- Created: 2025-12-29
-- Description: Tables for delivery zones, menu items, and menu categories

-- ============================================================
-- TABLE: menu_categories
-- ============================================================
CREATE TABLE IF NOT EXISTS public.menu_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(website_id, slug)
);

-- Index for faster queries
CREATE INDEX idx_menu_categories_website_id ON public.menu_categories(website_id);
CREATE INDEX idx_menu_categories_sort_order ON public.menu_categories(website_id, sort_order);

-- ============================================================
-- TABLE: menu_items
-- ============================================================
CREATE TABLE IF NOT EXISTS public.menu_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    category_id UUID REFERENCES public.menu_categories(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    image_url TEXT,
    is_available BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for faster queries
CREATE INDEX idx_menu_items_website_id ON public.menu_items(website_id);
CREATE INDEX idx_menu_items_category_id ON public.menu_items(category_id);
CREATE INDEX idx_menu_items_available ON public.menu_items(website_id, is_available);
CREATE INDEX idx_menu_items_sort_order ON public.menu_items(website_id, category_id, sort_order);

-- ============================================================
-- TABLE: delivery_zones
-- ============================================================
CREATE TABLE IF NOT EXISTS public.delivery_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    zone_name TEXT NOT NULL,
    delivery_fee DECIMAL(10,2) NOT NULL CHECK (delivery_fee >= 0),
    estimated_time TEXT,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for faster queries
CREATE INDEX idx_delivery_zones_website_id ON public.delivery_zones(website_id);
CREATE INDEX idx_delivery_zones_active ON public.delivery_zones(website_id, is_active);
CREATE INDEX idx_delivery_zones_sort_order ON public.delivery_zones(website_id, sort_order);

-- ============================================================
-- TRIGGERS: Auto-update updated_at timestamp
-- ============================================================

-- Trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER update_menu_categories_updated_at
    BEFORE UPDATE ON public.menu_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_menu_items_updated_at
    BEFORE UPDATE ON public.menu_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_delivery_zones_updated_at
    BEFORE UPDATE ON public.delivery_zones
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS
ALTER TABLE public.menu_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.delivery_zones ENABLE ROW LEVEL SECURITY;

-- Policies for menu_categories
CREATE POLICY "Users can view menu categories for their websites"
    ON public.menu_categories FOR SELECT
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert menu categories for their websites"
    ON public.menu_categories FOR INSERT
    WITH CHECK (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update menu categories for their websites"
    ON public.menu_categories FOR UPDATE
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete menu categories for their websites"
    ON public.menu_categories FOR DELETE
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

-- Policies for menu_items
CREATE POLICY "Users can view menu items for their websites"
    ON public.menu_items FOR SELECT
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert menu items for their websites"
    ON public.menu_items FOR INSERT
    WITH CHECK (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update menu items for their websites"
    ON public.menu_items FOR UPDATE
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete menu items for their websites"
    ON public.menu_items FOR DELETE
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

-- Policies for delivery_zones
CREATE POLICY "Users can view delivery zones for their websites"
    ON public.delivery_zones FOR SELECT
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert delivery zones for their websites"
    ON public.delivery_zones FOR INSERT
    WITH CHECK (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update delivery zones for their websites"
    ON public.delivery_zones FOR UPDATE
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete delivery zones for their websites"
    ON public.delivery_zones FOR DELETE
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE user_id = auth.uid()
        )
    );

-- ============================================================
-- PUBLIC READ ACCESS (for published websites)
-- ============================================================

-- Allow anonymous users to read menu data for published websites
CREATE POLICY "Public can view menu categories for published websites"
    ON public.menu_categories FOR SELECT
    USING (
        website_id IN (
            SELECT id FROM public.websites WHERE status = 'published'
        )
    );

CREATE POLICY "Public can view available menu items for published websites"
    ON public.menu_items FOR SELECT
    USING (
        is_available = true AND
        website_id IN (
            SELECT id FROM public.websites WHERE status = 'published'
        )
    );

CREATE POLICY "Public can view active delivery zones for published websites"
    ON public.delivery_zones FOR SELECT
    USING (
        is_active = true AND
        website_id IN (
            SELECT id FROM public.websites WHERE status = 'published'
        )
    );

-- ============================================================
-- COMMENTS (Documentation)
-- ============================================================

COMMENT ON TABLE public.menu_categories IS 'Menu categories for organizing menu items (e.g., Nasi, Lauk, Minuman)';
COMMENT ON TABLE public.menu_items IS 'Menu items with pricing and availability for restaurant websites';
COMMENT ON TABLE public.delivery_zones IS 'Delivery zones with fees and estimated times';

COMMENT ON COLUMN public.menu_items.price IS 'Price in MYR (Malaysian Ringgit)';
COMMENT ON COLUMN public.delivery_zones.delivery_fee IS 'Delivery fee in MYR (Malaysian Ringgit)';
COMMENT ON COLUMN public.delivery_zones.estimated_time IS 'Estimated delivery time (e.g., "30-45 min")';

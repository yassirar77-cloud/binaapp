-- =====================================================
-- BinaApp Delivery System - Test Data
-- Run this in Supabase SQL Editor to populate sample data
-- =====================================================

-- IMPORTANT: Replace 'YOUR_WEBSITE_ID_HERE' with your actual website ID
-- You can find this in the websites table in Supabase

-- =====================================================
-- 1. ADD DELIVERY ZONES
-- =====================================================
INSERT INTO delivery_zones (website_id, zone_name, delivery_fee, minimum_order, estimated_time_min, estimated_time_max)
VALUES
    ('YOUR_WEBSITE_ID_HERE', 'Downtown / Pusat Bandar', 5.00, 30.00, 25, 35),
    ('YOUR_WEBSITE_ID_HERE', 'Suburbs / Pinggir Bandar', 8.00, 35.00, 35, 50),
    ('YOUR_WEBSITE_ID_HERE', 'Airport Area / Kawasan Lapangan Terbang', 12.00, 40.00, 45, 60)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 2. ADD MENU CATEGORIES
-- =====================================================
INSERT INTO menu_categories (website_id, name, name_en, icon, sort_order)
VALUES
    ('YOUR_WEBSITE_ID_HERE', 'Nasi', 'Rice Dishes', '🍚', 1),
    ('YOUR_WEBSITE_ID_HERE', 'Lauk', 'Side Dishes', '🍗', 2),
    ('YOUR_WEBSITE_ID_HERE', 'Minuman', 'Beverages', '🥤', 3),
    ('YOUR_WEBSITE_ID_HERE', 'Pencuci Mulut', 'Desserts', '🍰', 4)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 3. ADD MENU ITEMS
-- Note: You'll need to get the category IDs first
-- =====================================================

-- Get category IDs (run this first to see the IDs):
-- SELECT id, name FROM menu_categories WHERE website_id = 'YOUR_WEBSITE_ID_HERE';

-- Replace CATEGORY_ID_NASI, CATEGORY_ID_LAUK, etc. with actual IDs from above query

-- Nasi (Rice) Items
INSERT INTO menu_items (website_id, category_id, name, description, price, image_url, is_popular)
VALUES
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_NASI', 'Nasi Lemak Special', 'Nasi lemak dengan sambal, ikan bilis, kacang, telur, timun', 8.50, 'https://images.unsplash.com/photo-1598514983318-2f64f8f4796c?w=400', true),
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_NASI', 'Nasi Ayam', 'Nasi ayam dengan sup dan sos kicap', 10.00, 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=400', true),
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_NASI', 'Nasi Briyani Kambing', 'Nasi briyani dengan kambing yang lembut', 15.00, 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400', false)
ON CONFLICT DO NOTHING;

-- Lauk (Side Dishes)
INSERT INTO menu_items (website_id, category_id, name, description, price, image_url, is_popular)
VALUES
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_LAUK', 'Ayam Goreng Berempah', 'Ayam goreng dengan rempah tradisional', 12.00, 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=400', true),
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_LAUK', 'Ikan Bakar', 'Ikan bakar dengan sambal', 18.00, 'https://images.unsplash.com/photo-1580959375944-1ab5ba8fc2a0?w=400', false),
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_LAUK', 'Rendang Daging', 'Rendang daging lembu yang lemak manis', 14.00, 'https://images.unsplash.com/photo-1580959375944-1ab5ba8fc2a0?w=400', true)
ON CONFLICT DO NOTHING;

-- Minuman (Beverages)
INSERT INTO menu_items (website_id, category_id, name, description, price, image_url)
VALUES
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_MINUMAN', 'Teh Tarik', 'Teh tarik panas', 3.50, 'https://images.unsplash.com/photo-1571934811356-5cc061b6821f?w=400'),
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_MINUMAN', 'Teh Ais', 'Teh ais sejuk', 3.00, 'https://images.unsplash.com/photo-1556881286-fc6915169721?w=400'),
    ('YOUR_WEBSITE_ID_HERE', 'CATEGORY_ID_MINUMAN', 'Air Kelapa', 'Air kelapa segar', 5.00, 'https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=400')
ON CONFLICT DO NOTHING;

-- =====================================================
-- 4. ADD DELIVERY SETTINGS
-- =====================================================
INSERT INTO delivery_settings (
    website_id,
    minimum_order,
    max_delivery_distance,
    notify_whatsapp,
    whatsapp_number,
    accept_cod,
    delivery_hours
)
VALUES (
    'YOUR_WEBSITE_ID_HERE',
    30.00,
    15.00,
    true,
    '+60123456789',
    true,
    '{
        "mon": {"open": "10:00", "close": "22:00", "closed": false},
        "tue": {"open": "10:00", "close": "22:00", "closed": false},
        "wed": {"open": "10:00", "close": "22:00", "closed": false},
        "thu": {"open": "10:00", "close": "22:00", "closed": false},
        "fri": {"open": "10:00", "close": "22:00", "closed": false},
        "sat": {"open": "10:00", "close": "23:00", "closed": false},
        "sun": {"open": "10:00", "close": "23:00", "closed": false}
    }'::jsonb
)
ON CONFLICT (website_id) DO UPDATE SET
    minimum_order = EXCLUDED.minimum_order,
    whatsapp_number = EXCLUDED.whatsapp_number;

-- =====================================================
-- 5. ADD A TEST RIDER (Optional)
-- =====================================================
INSERT INTO riders (
    website_id,
    name,
    phone,
    vehicle_type,
    vehicle_plate,
    is_active,
    is_online
)
VALUES
    ('YOUR_WEBSITE_ID_HERE', 'Ahmad Rider', '+60129876543', 'motorcycle', 'WXY1234', true, true),
    ('YOUR_WEBSITE_ID_HERE', 'Siti Rider', '+60187654321', 'motorcycle', 'ABC5678', true, false)
ON CONFLICT DO NOTHING;

-- =====================================================
-- DONE! Test data inserted.
-- =====================================================
SELECT 'Test data inserted successfully!' AS status;

-- =====================================================
-- VERIFICATION QUERIES
-- Run these to verify your data:
-- =====================================================

-- Check zones
-- SELECT zone_name, delivery_fee, minimum_order FROM delivery_zones WHERE website_id = 'YOUR_WEBSITE_ID_HERE';

-- Check categories
-- SELECT name, icon FROM menu_categories WHERE website_id = 'YOUR_WEBSITE_ID_HERE' ORDER BY sort_order;

-- Check menu items
-- SELECT name, price, is_popular FROM menu_items WHERE website_id = 'YOUR_WEBSITE_ID_HERE' ORDER BY price DESC;

-- Check riders
-- SELECT name, vehicle_type, is_online FROM riders WHERE website_id = 'YOUR_WEBSITE_ID_HERE';

-- Migration: Add missing delivery_settings fields for payment and fulfillment options
-- Run this in Supabase SQL Editor

-- Add new columns to delivery_settings table
ALTER TABLE delivery_settings
ADD COLUMN IF NOT EXISTS delivery_enabled BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS pickup_enabled BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS pickup_address TEXT,
ADD COLUMN IF NOT EXISTS qr_payment_image TEXT,
ADD COLUMN IF NOT EXISTS default_delivery_fee DECIMAL(10,2) DEFAULT 5.00;

-- Add comment for documentation
COMMENT ON COLUMN delivery_settings.delivery_enabled IS 'Whether delivery option is available';
COMMENT ON COLUMN delivery_settings.pickup_enabled IS 'Whether self-pickup option is available';
COMMENT ON COLUMN delivery_settings.pickup_address IS 'Address for self-pickup location';
COMMENT ON COLUMN delivery_settings.qr_payment_image IS 'URL to QR code image for payment';
COMMENT ON COLUMN delivery_settings.default_delivery_fee IS 'Default delivery fee when no zones are configured';

-- Update websites table to ensure business_type column exists
ALTER TABLE websites
ADD COLUMN IF NOT EXISTS business_type VARCHAR(50) DEFAULT 'general',
ADD COLUMN IF NOT EXISTS description TEXT;

COMMENT ON COLUMN websites.business_type IS 'Type of business: food, clothing, salon, services, bakery, general';
COMMENT ON COLUMN websites.description IS 'Business description for auto-detection of business type';

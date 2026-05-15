-- Migration 030: rider COD cash collection flag.
--
-- Adds a tristate column to record whether the rider received cash for a COD
-- delivery. NULL = not asked yet (default for non-COD orders or pre-migration
-- rows), TRUE = rider confirmed cash received, FALSE = rider marked delivered
-- but did NOT receive cash (dispute trail).
--
-- Apply manually to production after merge in the Supabase SQL editor.

ALTER TABLE delivery_orders
  ADD COLUMN IF NOT EXISTS payment_received BOOLEAN DEFAULT NULL;

COMMENT ON COLUMN delivery_orders.payment_received IS 'COD cash collected by rider';

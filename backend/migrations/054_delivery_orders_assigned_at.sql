-- =====================================================
-- 054_delivery_orders_assigned_at.sql
--
-- The rider accept flow (POST /delivery/riders/{id}/orders/{id}/accept)
-- writes delivery_orders.assigned_at when a rider claims a broadcast order.
-- The column exists in DATABASE_SCHEMA.sql (the reference schema) but was
-- never added by an applied migration, so production accepts failed with
-- PGRST204 "Could not find the 'assigned_at' column of 'delivery_orders'".
--
-- Apply in the Supabase SQL editor. Idempotent.
-- =====================================================

ALTER TABLE public.delivery_orders
  ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ;

COMMENT ON COLUMN public.delivery_orders.assigned_at IS
  'When a rider was assigned to the order (rider self-accept or manual assign).';

-- Ask PostgREST to refresh its schema cache immediately (Supabase also does
-- this automatically on DDL, but the NOTIFY makes it instant).
NOTIFY pgrst, 'reload schema';

-- =====================================================
-- Verification (run after applying)
-- =====================================================
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'delivery_orders' AND column_name = 'assigned_at';
-- -- expect 1 row

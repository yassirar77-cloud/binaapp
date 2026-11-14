-- Migration 064: dine-in orders from table QR codes
--
-- The QR toolkit already prints per-table posters whose code opens the
-- site with ?meja=<n>. Until now that marker went nowhere: the only order
-- type was delivery, which demands coordinates and a delivery zone.
--
-- A dine-in order has no delivery leg: no coordinates, no zone, no fee, no
-- rider. It moves pending -> confirmed -> preparing -> ready -> completed.
-- delivery_address stays NOT NULL (older readers expect it) and carries a
-- human label such as "Makan di kedai · Meja 5".

-- order_type already exists on some databases as a nullable column with
-- no default (ADD COLUMN IF NOT EXISTS then leaves it as it is). NULL means
-- delivery everywhere it is read, and passes both checks below.
ALTER TABLE public.delivery_orders
    ADD COLUMN IF NOT EXISTS order_type   TEXT NOT NULL DEFAULT 'delivery',
    ADD COLUMN IF NOT EXISTS table_number TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'delivery_orders_order_type_check'
    ) THEN
        ALTER TABLE public.delivery_orders
            ADD CONSTRAINT delivery_orders_order_type_check
            CHECK (order_type IN ('delivery', 'dine_in'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'delivery_orders_dine_in_has_table'
    ) THEN
        ALTER TABLE public.delivery_orders
            ADD CONSTRAINT delivery_orders_dine_in_has_table
            CHECK (order_type <> 'dine_in' OR table_number IS NOT NULL);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS delivery_orders_website_type_idx
    ON public.delivery_orders (website_id, order_type, created_at DESC);

COMMENT ON COLUMN public.delivery_orders.order_type IS
    'delivery (default) or dine_in (ordered from a table QR; no delivery leg).';
COMMENT ON COLUMN public.delivery_orders.table_number IS
    'Table label for dine_in orders, as printed on the table QR poster.';

NOTIFY pgrst, 'reload schema';

-- Migration 063: voucher codes and loyalty points for customer orders
--
-- Until now the checkout showed a hardcoded "BINAAPP10" discount that the
-- server never applied: the customer saw one total and was charged another.
-- This migration gives merchants real, server-validated promotions:
--
--   * vouchers            merchant-defined codes (percent or fixed RM off,
--                         optional cap, minimum order, date window, total
--                         and per-customer usage limits)
--   * voucher_redemptions one row per use, tied to the order
--   * loyalty_settings    per-site earn/redeem rates (off by default)
--   * loyalty_ledger      append-only points movements per customer phone
--
-- Money is always decided by the backend. The claim/redeem functions below
-- make the two limited resources race-safe:
--
--   claim_voucher           row-locks the voucher, so two checkouts cannot
--                           both take the last use
--   redeem_loyalty_points   advisory-locks (site, phone), so two checkouts
--                           cannot both spend the same balance
--
-- Points are earned when an order reaches delivered/completed and handed
-- back (with the voucher use) when it is cancelled or rejected. That lives
-- in a trigger because order status is written from several endpoints
-- (owner, rider, admin); the trigger swallows its own errors so a promo
-- problem can never block an order status change.
--
-- Only the backend (service role) touches these tables: RLS is on with no
-- policies, so anon/authenticated keys cannot read customer phones.

-- ---------------------------------------------------------------------------
-- Order columns
-- ---------------------------------------------------------------------------

ALTER TABLE public.delivery_orders
    ADD COLUMN IF NOT EXISTS discount_amount        NUMERIC(10, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS voucher_code           TEXT,
    ADD COLUMN IF NOT EXISTS loyalty_points_redeemed INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS loyalty_discount       NUMERIC(10, 2) NOT NULL DEFAULT 0;

-- discount_amount already exists on some databases as a NULLABLE column
-- (ADD COLUMN IF NOT EXISTS then leaves it as it is), so everything below
-- that reads these columns treats NULL as 0.
COMMENT ON COLUMN public.delivery_orders.discount_amount IS
    'Voucher discount in RM, already subtracted from total_amount.';
COMMENT ON COLUMN public.delivery_orders.loyalty_discount IS
    'Loyalty-points discount in RM, already subtracted from total_amount.';

-- ---------------------------------------------------------------------------
-- Vouchers
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.vouchers (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id         UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    code               TEXT NOT NULL CHECK (code ~ '^[A-Z0-9]{3,20}$'),
    description        TEXT NOT NULL DEFAULT '',
    discount_type      TEXT NOT NULL CHECK (discount_type IN ('percent', 'fixed')),
    discount_value     NUMERIC(10, 2) NOT NULL CHECK (discount_value > 0),
    -- Cap for percent vouchers ("10% off, max RM5"). NULL = no cap.
    max_discount       NUMERIC(10, 2) CHECK (max_discount IS NULL OR max_discount > 0),
    min_order          NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (min_order >= 0),
    starts_at          TIMESTAMPTZ,
    expires_at         TIMESTAMPTZ,
    usage_limit        INTEGER CHECK (usage_limit IS NULL OR usage_limit > 0),
    per_customer_limit INTEGER CHECK (per_customer_limit IS NULL OR per_customer_limit > 0),
    used_count         INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT vouchers_percent_range
        CHECK (discount_type <> 'percent' OR discount_value <= 100),
    CONSTRAINT vouchers_code_per_site UNIQUE (website_id, code)
);

CREATE TABLE IF NOT EXISTS public.voucher_redemptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voucher_id      UUID NOT NULL REFERENCES public.vouchers(id) ON DELETE CASCADE,
    website_id      UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    order_id        UUID REFERENCES public.delivery_orders(id) ON DELETE SET NULL,
    customer_phone  TEXT NOT NULL,
    discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS voucher_redemptions_voucher_phone_idx
    ON public.voucher_redemptions (voucher_id, customer_phone);
CREATE INDEX IF NOT EXISTS voucher_redemptions_order_idx
    ON public.voucher_redemptions (order_id);

-- ---------------------------------------------------------------------------
-- Loyalty
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.loyalty_settings (
    website_id     UUID PRIMARY KEY REFERENCES public.websites(id) ON DELETE CASCADE,
    enabled        BOOLEAN NOT NULL DEFAULT FALSE,
    -- Points earned per RM1 of the discounted food subtotal.
    points_per_rm  NUMERIC(6, 2) NOT NULL DEFAULT 1 CHECK (points_per_rm > 0 AND points_per_rm <= 100),
    -- Every `redeem_points` points are worth RM `redeem_value` off.
    redeem_points  INTEGER NOT NULL DEFAULT 100 CHECK (redeem_points > 0),
    redeem_value   NUMERIC(10, 2) NOT NULL DEFAULT 5 CHECK (redeem_value > 0),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.loyalty_ledger (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id     UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    customer_phone TEXT NOT NULL,
    order_id       UUID REFERENCES public.delivery_orders(id) ON DELETE SET NULL,
    -- Positive = earned / refunded / granted, negative = redeemed.
    points         INTEGER NOT NULL CHECK (points <> 0),
    reason         TEXT NOT NULL CHECK (reason IN ('earn', 'redeem', 'refund', 'adjust')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS loyalty_ledger_site_phone_idx
    ON public.loyalty_ledger (website_id, customer_phone);
-- An order earns once and is refunded once, however many times its status
-- is written.
CREATE UNIQUE INDEX IF NOT EXISTS loyalty_ledger_one_earn_per_order
    ON public.loyalty_ledger (order_id) WHERE reason = 'earn';
CREATE UNIQUE INDEX IF NOT EXISTS loyalty_ledger_one_refund_per_order
    ON public.loyalty_ledger (order_id) WHERE reason = 'refund';

CREATE OR REPLACE VIEW public.loyalty_balances
WITH (security_invoker = true) AS
SELECT website_id,
       customer_phone,
       SUM(points)::INTEGER                                  AS balance,
       SUM(points) FILTER (WHERE reason = 'earn')::INTEGER   AS lifetime_earned,
       MAX(created_at)                                       AS last_activity_at
FROM public.loyalty_ledger
GROUP BY website_id, customer_phone;

ALTER TABLE public.vouchers            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.voucher_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loyalty_settings    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.loyalty_ledger      ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- Race-safe claim / release
-- ---------------------------------------------------------------------------

-- Takes one use of a voucher for a customer. Returns the redemption id, or
-- NULL when the voucher is gone, inactive, outside its dates, or a limit
-- has been reached. The row lock makes concurrent claims queue up.
CREATE OR REPLACE FUNCTION public.claim_voucher(
    p_voucher_id UUID,
    p_phone      TEXT,
    p_discount   NUMERIC
) RETURNS UUID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v      public.vouchers%ROWTYPE;
    v_used INTEGER;
    v_id   UUID;
BEGIN
    SELECT * INTO v FROM public.vouchers WHERE id = p_voucher_id FOR UPDATE;
    IF NOT FOUND OR NOT v.is_active THEN
        RETURN NULL;
    END IF;
    IF v.starts_at IS NOT NULL AND now() < v.starts_at THEN
        RETURN NULL;
    END IF;
    IF v.expires_at IS NOT NULL AND now() >= v.expires_at THEN
        RETURN NULL;
    END IF;
    IF v.usage_limit IS NOT NULL AND v.used_count >= v.usage_limit THEN
        RETURN NULL;
    END IF;
    IF v.per_customer_limit IS NOT NULL THEN
        SELECT COUNT(*) INTO v_used
        FROM public.voucher_redemptions
        WHERE voucher_id = p_voucher_id AND customer_phone = p_phone;
        IF v_used >= v.per_customer_limit THEN
            RETURN NULL;
        END IF;
    END IF;

    UPDATE public.vouchers
    SET used_count = used_count + 1, updated_at = now()
    WHERE id = p_voucher_id;

    INSERT INTO public.voucher_redemptions (voucher_id, website_id, customer_phone, discount_amount)
    VALUES (p_voucher_id, v.website_id, p_phone, GREATEST(COALESCE(p_discount, 0), 0))
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

-- Hands a claimed use back (the order failed to save, or was cancelled).
CREATE OR REPLACE FUNCTION public.release_voucher(p_redemption_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v_voucher UUID;
BEGIN
    DELETE FROM public.voucher_redemptions
    WHERE id = p_redemption_id
    RETURNING voucher_id INTO v_voucher;
    IF v_voucher IS NULL THEN
        RETURN FALSE;
    END IF;
    UPDATE public.vouchers
    SET used_count = GREATEST(used_count - 1, 0), updated_at = now()
    WHERE id = v_voucher;
    RETURN TRUE;
END;
$$;

-- Spends points for a customer. Returns the ledger row id, or NULL when the
-- balance is too low. The advisory lock serialises spends per (site, phone).
CREATE OR REPLACE FUNCTION public.redeem_loyalty_points(
    p_website_id UUID,
    p_phone      TEXT,
    p_points     INTEGER
) RETURNS UUID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    v_balance INTEGER;
    v_id      UUID;
BEGIN
    IF p_points IS NULL OR p_points <= 0 THEN
        RETURN NULL;
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(p_website_id::TEXT || ':' || p_phone, 0));

    SELECT COALESCE(SUM(points), 0) INTO v_balance
    FROM public.loyalty_ledger
    WHERE website_id = p_website_id AND customer_phone = p_phone;

    IF v_balance < p_points THEN
        RETURN NULL;
    END IF;

    INSERT INTO public.loyalty_ledger (website_id, customer_phone, points, reason)
    VALUES (p_website_id, p_phone, -p_points, 'redeem')
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

REVOKE ALL ON FUNCTION public.claim_voucher(UUID, TEXT, NUMERIC)        FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_voucher(UUID)                     FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.redeem_loyalty_points(UUID, TEXT, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_voucher(UUID, TEXT, NUMERIC)        TO service_role;
GRANT EXECUTE ON FUNCTION public.release_voucher(UUID)                     TO service_role;
GRANT EXECUTE ON FUNCTION public.redeem_loyalty_points(UUID, TEXT, INTEGER) TO service_role;

-- ---------------------------------------------------------------------------
-- Earn on completion, give back on cancellation
-- ---------------------------------------------------------------------------

-- SECURITY DEFINER: order status is also written through the owner's RLS
-- client, which cannot see the promo tables.
CREATE OR REPLACE FUNCTION public.promo_on_order_status_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    s        public.loyalty_settings%ROWTYPE;
    v_points INTEGER;
    r        RECORD;
BEGIN
    BEGIN
        IF NEW.status IN ('delivered', 'completed')
           AND OLD.status NOT IN ('delivered', 'completed') THEN
            SELECT * INTO s FROM public.loyalty_settings WHERE website_id = NEW.website_id;
            IF FOUND AND s.enabled THEN
                v_points := FLOOR(
                    GREATEST(
                        NEW.subtotal
                        - COALESCE(NEW.discount_amount, 0)
                        - COALESCE(NEW.loyalty_discount, 0),
                        0
                    )
                    * s.points_per_rm
                );
                IF v_points > 0 THEN
                    INSERT INTO public.loyalty_ledger (website_id, customer_phone, order_id, points, reason)
                    VALUES (NEW.website_id, NEW.customer_phone, NEW.id, v_points, 'earn')
                    ON CONFLICT DO NOTHING;
                END IF;
            END IF;

        ELSIF NEW.status IN ('cancelled', 'rejected')
              AND OLD.status NOT IN ('cancelled', 'rejected') THEN
            IF COALESCE(NEW.loyalty_points_redeemed, 0) > 0 THEN
                INSERT INTO public.loyalty_ledger (website_id, customer_phone, order_id, points, reason)
                VALUES (NEW.website_id, NEW.customer_phone, NEW.id, NEW.loyalty_points_redeemed, 'refund')
                ON CONFLICT DO NOTHING;
            END IF;
            FOR r IN SELECT id FROM public.voucher_redemptions WHERE order_id = NEW.id LOOP
                PERFORM public.release_voucher(r.id);
            END LOOP;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'promo_on_order_status_change failed for order %: %', NEW.id, SQLERRM;
    END;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.promo_on_order_status_change() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS trg_promo_on_order_status_change ON public.delivery_orders;
CREATE TRIGGER trg_promo_on_order_status_change
    AFTER UPDATE OF status ON public.delivery_orders
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION public.promo_on_order_status_change();

COMMENT ON TABLE public.vouchers IS
    'Merchant voucher codes for customer orders. Backend-only (service role).';
COMMENT ON TABLE public.loyalty_ledger IS
    'Append-only loyalty points movements per (website, customer phone). Backend-only.';

NOTIFY pgrst, 'reload schema';

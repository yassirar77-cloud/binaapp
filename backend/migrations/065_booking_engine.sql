-- Migration 065: Booking engine (tempahan slot)
--
-- Until now "booking" on a salon / clinic / service site was a form whose
-- fields were pasted into a WhatsApp message: no availability, no record,
-- two customers could both be told "3pm is fine". This adds real slots.
--
--   booking_settings   one row per website: weekly opening hours, slot
--                      interval, how many customers one slot holds, how far
--                      ahead a slot may be booked.
--   booking_services   what can be booked (name, duration, price).
--   bookings           one customer appointment, with a short reference
--                      code (TP-XXXXXX) the customer keeps.
--
-- All times are stored as TIMESTAMPTZ. The business day (booking_date) and
-- the opening hours are in Malaysian time (UTC+8, no daylight saving); the
-- backend (services/booking_engine.py) does that conversion.
--
-- DOUBLE BOOKING. A slot is full when the number of active (pending /
-- confirmed) bookings overlapping it reaches capacity_per_slot. Checking
-- that in the application and then inserting is a race: two customers can
-- both read "1 seat left". create_booking() below does the count and the
-- insert in one transaction under a per-website-per-day advisory lock, so
-- concurrent requests for the same day queue up and the second one is
-- refused with SLOT_FULL. The backend only ever inserts through it.
--
-- Only the backend (service role) touches these tables; RLS is on with no
-- policies so the anon/authenticated keys cannot read customer phones.

CREATE TABLE IF NOT EXISTS public.booking_settings (
    website_id        UUID PRIMARY KEY REFERENCES public.websites(id) ON DELETE CASCADE,
    enabled           BOOLEAN NOT NULL DEFAULT false,
    slot_interval_min INTEGER NOT NULL DEFAULT 30
                      CHECK (slot_interval_min BETWEEN 5 AND 240),
    capacity_per_slot INTEGER NOT NULL DEFAULT 1
                      CHECK (capacity_per_slot BETWEEN 1 AND 50),
    -- Minimum notice: a slot starting sooner than this cannot be booked.
    lead_time_min     INTEGER NOT NULL DEFAULT 60
                      CHECK (lead_time_min BETWEEN 0 AND 10080),
    max_days_ahead    INTEGER NOT NULL DEFAULT 30
                      CHECK (max_days_ahead BETWEEN 1 AND 180),
    -- {"mon": [{"open": "09:00", "close": "18:00"}], "tue": [...], ...}
    -- A missing or empty day is closed. Several ranges = a lunch break.
    weekly_hours      JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- ["2026-12-25", ...] whole days off (public holidays, cuti).
    closed_dates      JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Shown to the customer on the booking page (deposit terms, parking…).
    note              TEXT NOT NULL DEFAULT '',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.booking_services (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id    UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    name          TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
    description   TEXT NOT NULL DEFAULT '',
    duration_min  INTEGER NOT NULL DEFAULT 30
                  CHECK (duration_min BETWEEN 5 AND 600),
    -- NULL = price not shown ("harga atas pertanyaan").
    price         NUMERIC(10, 2) CHECK (price IS NULL OR price >= 0),
    active        BOOLEAN NOT NULL DEFAULT true,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS booking_services_website_idx
    ON public.booking_services (website_id, sort_order);

CREATE TABLE IF NOT EXISTS public.bookings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id      UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    -- The service may later be edited or deleted; the name, duration and
    -- price the customer agreed to are copied onto the booking.
    service_id      UUID REFERENCES public.booking_services(id) ON DELETE SET NULL,
    service_name    TEXT NOT NULL,
    duration_min    INTEGER NOT NULL CHECK (duration_min BETWEEN 5 AND 600),
    price           NUMERIC(10, 2),
    reference       TEXT NOT NULL UNIQUE,
    -- The business day in Malaysian time, for day views and the lock key.
    booking_date    DATE NOT NULL,
    start_at        TIMESTAMPTZ NOT NULL,
    end_at          TIMESTAMPTZ NOT NULL,
    customer_name   TEXT NOT NULL CHECK (char_length(customer_name) BETWEEN 1 AND 120),
    customer_phone  TEXT NOT NULL,
    notes           TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'confirmed', 'cancelled',
                                      'completed', 'no_show')),
    cancelled_by    TEXT CHECK (cancelled_by IS NULL OR cancelled_by IN ('customer', 'owner')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_at > start_at)
);

CREATE INDEX IF NOT EXISTS bookings_website_date_idx
    ON public.bookings (website_id, booking_date, start_at);
CREATE INDEX IF NOT EXISTS bookings_website_phone_idx
    ON public.bookings (website_id, customer_phone);

ALTER TABLE public.booking_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.booking_services ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------
-- create_booking: the only insert path. Count + insert under a lock.
-- ---------------------------------------------------------------------
-- Raises 'SLOT_FULL' (SQLSTATE P0001) when the slot has no room left; the
-- backend turns that into HTTP 409. A duplicate reference raises the usual
-- unique violation (23505) and the backend retries with a new code.
--
-- The same phone number cannot hold two active bookings that overlap each
-- other on one website ('DUPLICATE_BOOKING'), which also makes a
-- double-tapped submit button harmless.

CREATE OR REPLACE FUNCTION public.create_booking(
    p_website_id      UUID,
    p_service_id      UUID,
    p_service_name    TEXT,
    p_duration_min    INTEGER,
    p_price           NUMERIC,
    p_reference       TEXT,
    p_booking_date    DATE,
    p_start_at        TIMESTAMPTZ,
    p_end_at          TIMESTAMPTZ,
    p_customer_name   TEXT,
    p_customer_phone  TEXT,
    p_notes           TEXT,
    p_capacity        INTEGER
) RETURNS public.bookings
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_taken   INTEGER;
    v_row     public.bookings;
BEGIN
    -- One lock per website per business day: bookings for different days
    -- or different websites never wait on each other.
    PERFORM pg_advisory_xact_lock(
        hashtextextended(p_website_id::text || ':' || p_booking_date::text, 0)
    );

    IF EXISTS (
        SELECT 1 FROM public.bookings
        WHERE website_id = p_website_id
          AND customer_phone = p_customer_phone
          AND status IN ('pending', 'confirmed')
          AND start_at < p_end_at
          AND end_at > p_start_at
    ) THEN
        RAISE EXCEPTION 'DUPLICATE_BOOKING' USING ERRCODE = 'P0001';
    END IF;

    SELECT count(*) INTO v_taken
    FROM public.bookings
    WHERE website_id = p_website_id
      AND status IN ('pending', 'confirmed')
      AND start_at < p_end_at
      AND end_at > p_start_at;

    IF v_taken >= GREATEST(p_capacity, 1) THEN
        RAISE EXCEPTION 'SLOT_FULL' USING ERRCODE = 'P0001';
    END IF;

    INSERT INTO public.bookings (
        website_id, service_id, service_name, duration_min, price, reference,
        booking_date, start_at, end_at, customer_name, customer_phone, notes
    ) VALUES (
        p_website_id, p_service_id, p_service_name, p_duration_min, p_price,
        p_reference, p_booking_date, p_start_at, p_end_at, p_customer_name,
        p_customer_phone, COALESCE(p_notes, '')
    )
    RETURNING * INTO v_row;

    RETURN v_row;
END;
$$;

REVOKE ALL ON FUNCTION public.create_booking(
    UUID, UUID, TEXT, INTEGER, NUMERIC, TEXT, DATE, TIMESTAMPTZ, TIMESTAMPTZ,
    TEXT, TEXT, TEXT, INTEGER
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_booking(
    UUID, UUID, TEXT, INTEGER, NUMERIC, TEXT, DATE, TIMESTAMPTZ, TIMESTAMPTZ,
    TEXT, TEXT, TEXT, INTEGER
) TO service_role;

COMMENT ON TABLE public.booking_settings IS
    'Per-website booking configuration (hours, slot size, capacity). Backend-only; see migration 065.';
COMMENT ON TABLE public.booking_services IS
    'Bookable services for the booking engine. Backend-only; see migration 065.';
COMMENT ON TABLE public.bookings IS
    'Customer appointments. Insert only through create_booking(). Backend-only; see migration 065.';

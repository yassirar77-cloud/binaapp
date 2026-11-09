-- Migration 062: mysyg.com surprise wishes
--
-- A wish is a small paid greeting page at https://<slug>.mysyg.com: the
-- sender's photos, a personal message, and a short Wan 3.0 video animated
-- from the main photo (with a generated soundtrack). No BinaApp account is
-- needed: the sender pays per wish through ToyyibPay and manages the wish
-- with a secret link (the token's SHA-256 is stored, never the token).
--
-- Flow (status):
--   awaiting_payment -> paid -> generating -> storing -> ready
--                                         \-> video_failed (page still live
--                                             with photos + message)
-- Each arrow is a conditional PATCH (WHERE status = <from>), so two
-- pollers racing on the same wish never submit or store a video twice.
--
-- Only the backend (service role) touches this table; RLS is on with no
-- policies so the anon/authenticated keys cannot read sender emails/phones.

CREATE TABLE IF NOT EXISTS public.wishes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug              TEXT NOT NULL UNIQUE
                      CHECK (slug ~ '^[a-z0-9](?:[a-z0-9-]{1,28}[a-z0-9])$'),
    status            TEXT NOT NULL DEFAULT 'awaiting_payment'
                      CHECK (status IN ('awaiting_payment', 'paid', 'generating',
                                        'storing', 'ready', 'video_failed',
                                        'cancelled')),
    occasion          TEXT NOT NULL DEFAULT 'birthday',
    sender_name       TEXT NOT NULL,
    recipient_name    TEXT NOT NULL,
    message           TEXT NOT NULL,
    music_style       TEXT NOT NULL DEFAULT 'romantic_piano',
    photo_urls        JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Payer details (ToyyibPay requires them); private, never rendered.
    payer_email       TEXT NOT NULL,
    payer_phone       TEXT NOT NULL,
    edit_token_hash   TEXT NOT NULL,
    amount_rm         NUMERIC(8, 2) NOT NULL,
    bill_code         TEXT UNIQUE,
    paid_at           TIMESTAMPTZ,
    toyyibpay_transaction_id TEXT,
    -- Video generation
    video_prompt      TEXT,
    video_task_id     TEXT,
    video_provider    TEXT,
    video_attempts    INTEGER NOT NULL DEFAULT 0,
    video_url         TEXT,
    poster_url        TEXT,
    video_error       TEXT,
    video_started_at  TIMESTAMPTZ,
    last_polled_at    TIMESTAMPTZ,
    view_count        INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS wishes_status_idx ON public.wishes (status);

ALTER TABLE public.wishes ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.wishes IS
    'mysyg.com surprise wish pages (<slug>.mysyg.com). Backend-only; see migration 062.';

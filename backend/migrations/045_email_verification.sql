-- ==========================================================================
-- Migration 045: Email verification (block-at-publish/pay model)
-- ==========================================================================
-- Adds the state needed to require email ownership before a user can
-- publish a website or pay. Registration stays frictionless: the account
-- and custom JWT are still issued immediately (see auth.py /register), so
-- a new user can sign up and use the builder right away. The gate is
-- enforced server-side at the publish + payment endpoints, which read the
-- profiles.email_verified flag set here.
--
-- This is intentionally DECOUPLED from Supabase Auth's own "Confirm email"
-- setting: registration still creates the auth user with email_confirm=true
-- so the existing password-grant login keeps working unchanged. The flag
-- below is our independent source of truth.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS + CREATE TABLE IF NOT EXISTS.
-- ==========================================================================

BEGIN;

-- 1. Verification flag on profiles (the gate reads this).
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;

-- 2. Grandfather all EXISTING accounts as verified.
--    Critical: existing real users (created before this feature) must NOT be
--    locked out of publish/pay. Only accounts created from now on start
--    unverified. New rows default to false via the column default above.
UPDATE public.profiles
SET email_verified = true,
    email_verified_at = COALESCE(email_verified_at, NOW())
WHERE email_verified = false;

-- 3. One-time verification codes. We store a SHA-256 hash of the code, never
--    the code itself. Codes are short-lived and attempt-limited; verification
--    requires an authenticated session (the user's own JWT), so the practical
--    attack surface for brute force is the legitimate session only.
CREATE TABLE IF NOT EXISTS public.email_verification_codes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    code_hash   TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    attempts    INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_verification_codes_user
    ON public.email_verification_codes (user_id);

-- RLS: only the backend (service role) touches this table. Enable RLS with
-- no permissive policies so the anon/auth roles cannot read codes directly;
-- the service role bypasses RLS.
ALTER TABLE public.email_verification_codes ENABLE ROW LEVEL SECURITY;

COMMIT;

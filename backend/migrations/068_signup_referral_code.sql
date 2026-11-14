-- Migration 068: remember the referral code an account signed up with
--
-- A referral link is https://binaapp.my/register?ref=BINA-XXXX-XXXX. The
-- register endpoint stores the code here; it is applied (referral_history
-- row + BinaCredit for both sides) when the account's email is verified,
-- so a referral only pays out for an account with a real inbox.
--
-- Additive and idempotent.

ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS signup_ref_code TEXT
    CHECK (signup_ref_code IS NULL OR signup_ref_code ~ '^BINA-[A-Z0-9]{4}-[A-Z0-9]{4}$');

COMMENT ON COLUMN public.profiles.signup_ref_code IS
    'Referral code the account registered with (applied on email verification). See migration 068.';

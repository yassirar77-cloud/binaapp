-- Migration 046: Add websites.promoted_bill_code column
--
-- Background: _promote_pending_draft_for_user() turns a status='pending_payment'
-- draft into a live site after a subscription payment. It used to select the
-- user's MOST-RECENT pending_payment draft keyed only on user_id, with no link
-- to the bill that paid for it. That had two failure modes:
--
--   1. The promotion is invoked from several places for the SAME payment (the
--      ToyyibPay webhook callback, the frontend verify-payment endpoint, and the
--      recover-pending sweep). Because each invocation re-selected "most-recent
--      pending_payment draft", once the first promoted draft D3 flipped to
--      published, a second invocation for the same payment would promote a
--      DIFFERENT draft (D2) — so one RM5 payment could publish several drafts.
--   2. It ran with no quota check, so a renewal/upgrade could push a user past
--      their plan's website limit.
--
-- This column lets promotion CLAIM a specific draft for a specific bill via an
-- atomic conditional UPDATE (WHERE status='pending_payment' AND
-- promoted_bill_code IS NULL). A given bill then promotes at most one specific
-- draft, and concurrent invocations for the same payment can no longer each
-- promote a different draft. (The promotion code also gates on
-- check_limit("create_website") so it can never exceed the website limit.)
--
-- Safety: IF NOT EXISTS makes this idempotent. The promotion code degrades
-- gracefully when this column is absent (the quota gate still applies; only the
-- per-bill race guard is disabled), so deploying the code before this migration
-- is safe. No UNIQUE constraint: a bill legitimately maps to one draft, but we
-- never want a write to hard-fail on a duplicate; the conditional claim handles
-- single-promotion semantics.

ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS promoted_bill_code TEXT NULL;

-- Partial index to make the per-bill idempotency lookup
-- (promoted_bill_code = eq.<bill>) cheap without bloating the table.
CREATE INDEX IF NOT EXISTS idx_websites_promoted_bill_code
  ON public.websites (promoted_bill_code)
  WHERE promoted_bill_code IS NOT NULL;

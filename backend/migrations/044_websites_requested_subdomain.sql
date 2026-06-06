-- Migration 044: Add websites.requested_subdomain column
--
-- Background: a user who builds a site on a free account types their chosen
-- PROJECT NAME and SUBDOMAIN in the publish modal, but is then diverted to
-- the payment/upgrade flow before /api/publish ever runs. Their site is only
-- persisted as a status='pending_payment' draft, and after payment the draft
-- is turned live by _promote_pending_draft_for_user(). That promotion used to
-- regenerate the subdomain from the (AI-derived) business name — so the
-- subdomain the user explicitly picked at build time ("merto") was discarded
-- in favour of a slug like "modern-hair-salon-2".
--
-- We now persist the user's chosen subdomain on the draft at build time so
-- promotion can honour it. It lives in a DEDICATED column rather than the
-- existing `subdomain` column because `subdomain` is UNIQUE (migration 001):
-- storing the real chosen value on an unpublished draft would risk a UNIQUE
-- collision (e.g. the user regenerates and a second draft wants the same
-- subdomain). The live `subdomain` column keeps its placeholder
-- 'draft-<uuid>' until promotion resolves a final, uniqueness-checked value.
--
-- Safety: IF NOT EXISTS guard makes this idempotent — re-running on a database
-- where the column already exists is a no-op. No UNIQUE constraint here on
-- purpose: this is the user's *requested* value, validated/deduped at promote.

ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS requested_subdomain VARCHAR(63) NULL;

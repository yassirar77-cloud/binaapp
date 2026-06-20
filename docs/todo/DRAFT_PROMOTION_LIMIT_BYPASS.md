# RESOLVED: pending_payment draft promotion could exceed the website limit / publish multiple drafts per payment

**Severity:** High — billing bypass (one RM5 payment could yield more published sites than the plan allows)
**Status:** FIXED on the billing branch (see "Fix" below). Requires migration 046.

## Problem

A user can create unlimited `status='pending_payment'` website drafts at zero
quota cost — every website-count query excludes them
(`subscription_service.get_actual_resource_counts` uses `status=neq.pending_payment`,
likewise `websites.py:77`, `main.py:2554`). "Quota gates publishing, not saving."

After a subscription payment, `_promote_pending_draft_for_user`
(`payments.py`) flips a draft `pending_payment → published`. As written it had
two defects:

1. **No quota check.** It promoted the user's *most-recent* `pending_payment`
   draft and called `increment_usage("create_website")` with no
   `check_limit`. So any subscription payment — including a **renewal**, which
   only entitles keeping the existing site — would silently publish a waiting
   draft, pushing `websites_count` past `websites_limit` with no reconciliation.

2. **Keyed on "most-recent draft by user_id", not the bill.** Promotion is
   invoked from several places for the SAME payment: the ToyyibPay webhook
   callback (`payments.py:761`), the frontend `verify-payment` endpoint
   (`subscription.py:893`), the legacy callback/verify (`payments.py:1178`,
   `:1401`), and `recover-pending`. The per-transaction idempotency guard
   (skip if `payment_status == "success"`) covers the common *sequential*
   case, but under a true race (webhook + verify-payment both see the
   transaction still pending — common on a cold Render dyno) each invocation
   re-selected "most-recent draft": the first promoted D3, the second then
   promoted D2 → **two sites published from one RM5 payment**.

Manual publish (`POST /api/publish`, `simple/publish.py:506`) was NOT affected —
it already enforces `check_limit` and 403s when over limit. There is also **no
cleanup** of abandoned drafts (the `ai_proactive_monitor` `pending_payment`
handler is for `delivery_orders`, a different table), so drafts accumulate as
latent "free publishes" waiting for the next payment.

## Impact

- A Starter user (`websites_limit=1`) with one published site could get a second
  draft auto-published for free on their next RM5 renewal.
- A user who stockpiles drafts and pays once could, under the callback/verify
  race, get several published at once.
- `websites_count` drifts above `websites_limit`; nothing reconciles it (no
  downgrade/over-limit clawback exists).

## Fix (applied)

`_promote_pending_draft_for_user(user_id, bill_code)`:

1. **Quota gate** — calls `subscription_service.check_limit("create_website")`
   and refuses to promote when not allowed (leaves the draft `pending_payment`).
   Fails open only on an unexpected `check_limit` exception so a genuinely paid
   site still goes live. Also consumes a `website` addon credit when the slot
   came from one (`using_addon`), mirroring `create_website`.
2. **Per-bill claim** — a new nullable column `websites.promoted_bill_code`
   (migration 046) lets promotion atomically CLAIM a specific draft for a
   specific bill via a conditional update
   (`WHERE status='pending_payment' AND promoted_bill_code IS NULL`). A given
   bill promotes at most one specific draft; concurrent invocations for one
   payment converge (the loser gets 0 rows and no-ops instead of promoting a
   different draft). An up-front lookup short-circuits when this bill already
   promoted a draft.

All four call sites now pass `bill_code`. The code **degrades gracefully** when
migration 046 is absent (quota gate still applies; only the per-bill race guard
is disabled), so deploying the code before running the migration is safe.

## Migration dependency

`backend/migrations/046_websites_promoted_bill_code.sql` —
`ALTER TABLE public.websites ADD COLUMN IF NOT EXISTS promoted_bill_code TEXT` +
partial index. Apply it to get the full per-bill race guard.

## Verification

Logic exercised against a mocked PostgREST/httpx layer (6 scenarios, all pass):
quota-block (no publish), per-bill idempotency (same bill no-ops), lost-claim
race (concurrent invocation no-ops, no second draft), happy path (publish +
increment), addon-slot path (consumes a `website` credit), and column-missing
degradation (still gated, still publishes).

## Follow-ups (not in this change)

- Consider a cleanup job for abandoned `pending_payment` drafts older than N days.
- Renewals don't carry a "target draft" intent; the quota gate makes promoting a
  waiting draft on renewal harmless (bounded by the limit), but a future
  refinement could record the intended draft at bill-creation time so only the
  initial subscribe bill promotes.

-- Backfill subscriptions.plan_id for rows where it is NULL.
--
-- The backend historically never wrote subscriptions.plan_id, so the
-- can_publish_subdomain publish gate AND the websites_limit quota joins —
-- both of which embed subscription_plans VIA plan_id — resolved against NULL
-- and behaved as if the user had no plan (paid users blocked, public site
-- served the upgrade paywall even after paying).
--
-- The payment flow now writes plan_id on every new payment. This migration
-- heals existing rows by matching the subscription's tier to the plan's
-- plan_name (e.g. tier='starter' -> subscription_plans.plan_name='starter').
--
-- Idempotent and safe to re-run: only NULL plan_id rows are touched, and rows
-- whose tier has no matching plan (e.g. 'free' with no free plan row) are left
-- untouched rather than mismatched.
--
-- NOTE: this fixes the gate for already-paid users. It does NOT promote their
-- pre-payment draft websites (status='pending_payment') to live — those were
-- never uploaded to storage and need the application-side promotion, not SQL.

UPDATE public.subscriptions AS s
SET plan_id = p.id,
    updated_at = NOW()
FROM public.subscription_plans AS p
WHERE s.plan_id IS NULL
  AND s.tier = p.plan_name;

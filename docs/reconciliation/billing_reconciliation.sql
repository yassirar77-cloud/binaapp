-- =====================================================================
-- BinaApp — billing-integrity reconciliation (READ-ONLY)
-- =====================================================================
-- Purpose: quantify exposure from the rider quota-bypass and the
-- never-consumed addon credits, BEFORE merging the enforcement fixes.
--
-- Safe to run on production: every statement is a SELECT. No writes.
-- Run each block separately in the Supabase SQL editor.
--
-- Assumed columns (adjust if your schema differs):
--   subscriptions(user_id, tier, status, end_date, current_period_end, created_at)
--   addon_purchases(user_id, addon_type, quantity, quantity_used, status,
--                   unit_price, total_price, created_at, expires_at)
--   websites(id, user_id)        riders(id, website_id, is_active)
-- Rider base slots per tier: pro = 10, everyone else (free/starter/basic) = 0.
-- (Swap the CASE for a join on subscription_plans.riders_limit if you prefer.)
-- =====================================================================


-- ---------------------------------------------------------------------
-- [A] RIDER EXPOSURE — per merchant: how many riders exist beyond what
--     their plan + purchased rider credits actually entitle them to.
--     uncovered_riders = riders that should have required a paid RM3 slot.
-- ---------------------------------------------------------------------
WITH cur_sub AS (
  SELECT DISTINCT ON (user_id)
         user_id, tier, status
  FROM public.subscriptions
  ORDER BY user_id,
           current_period_end DESC NULLS LAST,  -- drop this line if column absent
           end_date          DESC NULLS LAST,
           created_at        DESC
),
rider_base AS (
  SELECT user_id, tier, status,
         CASE lower(COALESCE(tier,'starter'))
           WHEN 'pro' THEN 10
           ELSE 0
         END AS riders_base_limit
  FROM cur_sub
),
rider_counts AS (
  SELECT w.user_id, COUNT(r.id) AS riders_created
  FROM public.websites w
  JOIN public.riders   r ON r.website_id = w.id
  -- AND r.is_active           -- uncomment to count only active riders
  GROUP BY w.user_id
),
rider_credits AS (
  SELECT user_id,
         SUM(GREATEST(0, quantity - COALESCE(quantity_used,0))) AS rider_credits_available
  FROM public.addon_purchases
  WHERE addon_type = 'rider' AND status = 'active'
  GROUP BY user_id
)
SELECT
  rb.user_id,
  rb.tier,
  rb.status                                   AS sub_status,
  rb.riders_base_limit,
  COALESCE(rc.riders_created, 0)              AS riders_created,
  COALESCE(cr.rider_credits_available, 0)     AS rider_credits_available,
  GREATEST(0, COALESCE(rc.riders_created,0)
              - rb.riders_base_limit
              - COALESCE(cr.rider_credits_available,0)) AS uncovered_riders,
  GREATEST(0, COALESCE(rc.riders_created,0)
              - rb.riders_base_limit
              - COALESCE(cr.rider_credits_available,0)) * 3.00 AS revenue_at_risk_rm
FROM rider_base rb
LEFT JOIN rider_counts  rc ON rc.user_id = rb.user_id
LEFT JOIN rider_credits cr ON cr.user_id = rb.user_id
WHERE COALESCE(rc.riders_created,0) > 0
ORDER BY uncovered_riders DESC, riders_created DESC;


-- ---------------------------------------------------------------------
-- [A2] RIDER EXPOSURE — single-row total (RM at risk across all merchants)
-- ---------------------------------------------------------------------
WITH cur_sub AS (
  SELECT DISTINCT ON (user_id) user_id, tier
  FROM public.subscriptions
  ORDER BY user_id, current_period_end DESC NULLS LAST,
           end_date DESC NULLS LAST, created_at DESC
),
rider_base AS (
  SELECT user_id,
         CASE lower(COALESCE(tier,'starter')) WHEN 'pro' THEN 10 ELSE 0 END AS riders_base_limit
  FROM cur_sub
),
rider_counts AS (
  SELECT w.user_id, COUNT(r.id) AS riders_created
  FROM public.websites w JOIN public.riders r ON r.website_id = w.id
  GROUP BY w.user_id
),
rider_credits AS (
  SELECT user_id, SUM(GREATEST(0, quantity - COALESCE(quantity_used,0))) AS avail
  FROM public.addon_purchases WHERE addon_type='rider' AND status='active' GROUP BY user_id
)
SELECT
  COUNT(*) FILTER (WHERE COALESCE(rc.riders_created,0) > 0)                       AS merchants_with_riders,
  COALESCE(SUM(rc.riders_created),0)                                             AS total_riders,
  SUM(GREATEST(0, COALESCE(rc.riders_created,0) - rb.riders_base_limit
                  - COALESCE(cr.avail,0)))                                        AS total_uncovered_riders,
  SUM(GREATEST(0, COALESCE(rc.riders_created,0) - rb.riders_base_limit
                  - COALESCE(cr.avail,0))) * 3.00                                 AS total_rider_revenue_at_risk_rm
FROM rider_base rb
LEFT JOIN rider_counts  rc ON rc.user_id = rb.user_id
LEFT JOIN rider_credits cr ON cr.user_id = rb.user_id;


-- ---------------------------------------------------------------------
-- [B] RIDER CREDIT LEDGER — who actually bought rider addons, and whether
--     any were ever consumed (pre-fix, quantity_used should be ~0).
-- ---------------------------------------------------------------------
SELECT user_id, quantity, quantity_used,
       GREATEST(0, quantity - COALESCE(quantity_used,0)) AS available,
       status, unit_price, total_price, created_at, expires_at
FROM public.addon_purchases
WHERE addon_type = 'rider'
ORDER BY user_id, created_at;


-- ---------------------------------------------------------------------
-- [C] UNCONSUMED AI CREDITS — ai_hero / ai_image credits bought but never
--     drawn down (the "permanent monthly boost" leak). After the fix these
--     start depleting; this shows the standing balance you're carrying.
-- ---------------------------------------------------------------------
SELECT
  user_id,
  addon_type,
  SUM(quantity)                                           AS credits_purchased,
  SUM(COALESCE(quantity_used,0))                          AS credits_used,
  SUM(GREATEST(0, quantity - COALESCE(quantity_used,0)))  AS credits_unconsumed
FROM public.addon_purchases
WHERE addon_type IN ('ai_hero','ai_image') AND status = 'active'
GROUP BY user_id, addon_type
HAVING SUM(GREATEST(0, quantity - COALESCE(quantity_used,0))) > 0
ORDER BY credits_unconsumed DESC;


-- ---------------------------------------------------------------------
-- [D] GLOBAL ADDON SUMMARY — one row per addon type. Pre-fix you expect
--     units_consumed ≈ 0 for every type EXCEPT website (the only one that
--     consumed). This is the headline "decorative billing" exposure.
-- ---------------------------------------------------------------------
SELECT
  addon_type,
  COUNT(DISTINCT user_id)                                 AS buyers,
  SUM(quantity)                                           AS units_purchased,
  SUM(COALESCE(quantity_used,0))                          AS units_consumed,
  SUM(GREATEST(0, quantity - COALESCE(quantity_used,0)))  AS units_outstanding,
  ROUND(SUM(COALESCE(total_price,0))::numeric, 2)         AS gross_rm_collected
FROM public.addon_purchases
WHERE status IN ('active','depleted')
GROUP BY addon_type
ORDER BY addon_type;


-- ---------------------------------------------------------------------
-- [E] ZONE CREDITS (context only) — zone addons anyone bought. Zone
--     enforcement/consumption is intentionally NOT wired yet, so these are
--     inert today. Lists them so you can decide honor-vs-refund when you
--     make the zone pricing call.
-- ---------------------------------------------------------------------
SELECT user_id, quantity, quantity_used, status, unit_price, total_price, created_at
FROM public.addon_purchases
WHERE addon_type = 'zone'
ORDER BY created_at;

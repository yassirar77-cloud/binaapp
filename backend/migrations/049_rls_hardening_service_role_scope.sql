-- =============================================================================
-- Migration 049: RLS hardening — scope service-role-only policies away from anon
-- =============================================================================
--
-- ROOT CAUSE
--   Many policies intended for the service-role backend were written as
--   `USING (true)` (and/or `WITH CHECK (true)`) with no `TO` clause, so they
--   apply to roles = {public}  →  every browser holding the public anon key can
--   read/write these tables directly via PostgREST / supabase-js.
--
--   The FastAPI backend authenticates with the SERVICE-ROLE key and BYPASSES RLS
--   entirely, so tightening these policies does NOT affect any backend code path.
--   These permissive policies are pure anon-key attack surface.
--
--   All tables touched here already have RLS ENABLED — no `ALTER TABLE ... ENABLE
--   ROW LEVEL SECURITY` is required.
--
-- FRONTEND ANON-KEY EXPOSURE (grepped frontend/src before writing this):
--   The browser supabase-js client runs PERMANENTLY on the `anon` role
--   (lib/supabase.ts: login stores a custom backend JWT, never calls
--   supabase.auth.setSession(); auth.uid() is NULL). Consequences per table are
--   annotated inline below as [FRONTEND ...].
--
--   >>> ONE REAL BREAKAGE <<<
--   components/dashboard/DashboardTab.tsx reads FOUR of these tables DIRECTLY via
--   the anon client (all SELECT, no writes):
--       delivery_orders     (DashboardTab.tsx:156)
--       order_items         (DashboardTab.tsx:175)
--       chat_conversations  (DashboardTab.tsx:215)
--       chat_messages       (DashboardTab.tsx:232)
--   Those reads currently succeed ONLY because of the `USING(true)` public
--   policies dropped below (the owner-via-join policies return 0 rows for anon).
--   After this migration the dashboard's Orders + Chat analytics panels will read
--   0 rows until those four queries are moved to a service-role backend endpoint
--   (or the app starts issuing real Supabase-signed sessions). No customer-facing
--   flow breaks: there are NO frontend writes to these tables — customer chat,
--   checkout, and order tracking already go through the backend.
--
-- NAME-DRIFT WARNING
--   Policy names differ across the repo's three migration lineages and prod.
--   Every DROP uses IF EXISTS, so a name that doesn't exist is a harmless no-op —
--   but that also means a wrong/renamed prod policy is silently NOT dropped.
--   The names below combine (a) the names from the pg_policies review and
--   (b) repo-migration variants for the same table. RECONCILE against a live
--   `SELECT * FROM pg_policies` dump before trusting this, and run the
--   verification query at the very bottom AFTER applying to confirm no
--   `qual = true` public policies remain.
--
-- Reusable service-role predicate used throughout: auth.role() = 'service_role'
-- (matches the correct pattern already used by migration 015 for payments/addon).
-- Note: service_role bypasses RLS, so a `TO service_role` policy is effectively
-- documentation of intent; the security effect comes from REMOVING the public
-- USING(true) policy, not from adding the scoped one.
-- =============================================================================

BEGIN;

-- =============================================================================
-- SECTION 1 — CRITICAL: drop outright (no replacement write policy)
-- =============================================================================

-- 1a. subscriptions — tier/status changes must go through the service-role
--     backend only. A stray public UPDATE here = "grant myself an active/pro sub".
-- [FRONTEND] lib/quota.ts:105 does .from('subscriptions').select(...) via anon,
--     but that read already returns 0 rows today (anon uid=NULL vs owner policy)
--     and quota.ts already falls back to the backend. Dropping the UPDATE adds no
--     new breakage. We (re)assert a SELECT-ONLY owner policy for defense-in-depth
--     and for any future Supabase-signed sessions — NOT an update policy.
DROP POLICY IF EXISTS "Users can update own subscription" ON public.subscriptions;

DROP POLICY IF EXISTS "Users can view own subscription" ON public.subscriptions;
CREATE POLICY "Users can view own subscription"
    ON public.subscriptions
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);
-- (Existing correctly-scoped "Service role manages ..." policy on subscriptions
--  is intentionally left untouched — see DO NOT TOUCH list.)

-- 1b. delivery_orders — bulk customer-PII read (name/phone/address) by anon.
--     Customer order tracking goes through the backend, not this policy.
-- [FRONTEND] DashboardTab.tsx:156 reads delivery_orders via anon (SELECT only) —
--     see ONE REAL BREAKAGE note in the header. No frontend writes.
-- NOTE: we drop ONLY the public READ policies here. The public INSERT policies
--     ("public_can_create_orders" / "Anyone can create orders") are LEFT IN PLACE
--     (out of scope for this migration; customer checkout historically relied on
--     them, though it now runs through the backend). The owner-via-join view
--     policies are also kept.
DROP POLICY IF EXISTS "Anyone can track orders by number" ON public.delivery_orders;
DROP POLICY IF EXISTS "public_can_track_orders"          ON public.delivery_orders;

-- =============================================================================
-- SECTION 2 — CRITICAL: narrow from public USING(true) to service_role
-- =============================================================================

-- 2a. bina_credits — user wallet balance. Only the user may read their own row;
--     only the backend may mint/spend. (Backend keys wallet rows by user_id.)
-- [FRONTEND] no direct anon access found (grep clean). Backend-only writes.
DROP POLICY IF EXISTS "System insert wallet" ON public.bina_credits;
DROP POLICY IF EXISTS "System update wallet" ON public.bina_credits;

CREATE POLICY "Service role inserts wallet"
    ON public.bina_credits
    FOR INSERT
    TO service_role
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role updates wallet"
    ON public.bina_credits
    FOR UPDATE
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
-- Keep "Users view own wallet" (auth.uid() = user_id) — untouched.

-- 2b. promo_config — promo campaign internals. Despite the name, the prod policy
--     is FOR ALL USING(true) roles={public} (migration 047). Anon could read/edit
--     campaign config. Scope to service_role.
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Service role manages promo config" ON public.promo_config;
CREATE POLICY "Service role manages promo config"
    ON public.promo_config
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 2c. promo_redemptions — same FOR ALL USING(true) problem (anon could forge a
--     redemption). Scope the management policy; keep the user-view policy.
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Service role manages promo redemptions" ON public.promo_redemptions;
CREATE POLICY "Service role manages promo redemptions"
    ON public.promo_redemptions
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
-- Keep "Users can view own promo redemption" (auth.uid() = user_id) — untouched.

-- =============================================================================
-- SECTION 3 — HIGH: narrow public USING(true) → service_role
--   Pattern for each table: drop the permissive public policy/policies, then
--   assert a single canonical service_role FOR ALL policy. Owner (auth.uid())
--   and properly-conditioned public-read policies are preserved (not listed).
-- =============================================================================

-- 3a. chat_messages — customer chat content (the pg_policies review lists 4
--     permissive policies; repo lineages add more name variants — all dropped
--     via IF EXISTS). Also on the supabase_realtime publication (anon could
--     stream every chat) — REMOVING these policies closes the realtime read too.
-- [FRONTEND] DashboardTab.tsx:232 reads chat_messages via anon (SELECT only) —
--     BREAKS the dashboard chat panel (see header). No frontend writes; the
--     customer chat widget posts through the backend.
DROP POLICY IF EXISTS "Allow all chat_messages"   ON public.chat_messages;
DROP POLICY IF EXISTS "chat_messages_all"          ON public.chat_messages;
DROP POLICY IF EXISTS "Anyone can view messages"   ON public.chat_messages;
DROP POLICY IF EXISTS "Anyone can insert messages" ON public.chat_messages;
DROP POLICY IF EXISTS "Anyone can update messages" ON public.chat_messages;
DROP POLICY IF EXISTS "Service role full access to messages" ON public.chat_messages;
CREATE POLICY "Service role manages chat_messages"
    ON public.chat_messages
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3b. chat_conversations — customer name/phone. Same treatment as 3a.
-- [FRONTEND] DashboardTab.tsx:215 reads chat_conversations via anon (SELECT only)
--     — BREAKS the dashboard chat list (see header). No frontend writes.
--     Owner policies ("Owners can view/manage own conversations") are KEPT — they
--     just don't help the anon session (uid NULL).
DROP POLICY IF EXISTS "Allow all chat_conversations"       ON public.chat_conversations;
DROP POLICY IF EXISTS "chat_conversations_all"             ON public.chat_conversations;
DROP POLICY IF EXISTS "Anyone can create conversations"    ON public.chat_conversations;
DROP POLICY IF EXISTS "Service role full access to conversations" ON public.chat_conversations;
CREATE POLICY "Service role manages chat_conversations"
    ON public.chat_conversations
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3c. order_items — drop the public READ policies only (keep public INSERT used
--     by the historical checkout path: "public_can_create_order_items").
-- [FRONTEND] DashboardTab.tsx:175 reads order_items via anon (SELECT only) —
--     BREAKS the dashboard revenue/items breakdown (see header). No frontend writes.
DROP POLICY IF EXISTS "Anyone can view order items"   ON public.order_items;
DROP POLICY IF EXISTS "public_can_view_order_items"   ON public.order_items;
CREATE POLICY "Service role manages order_items"
    ON public.order_items
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3d. order_status_history — drop public READ + the public "system_can_insert".
-- [FRONTEND] no direct anon access found (grep clean).
-- !! CAUTION — VERIFY BEFORE APPLYING !!
--    order_status_history is populated by a trigger on delivery_orders
--    (migration 007). If that trigger function runs as the INVOKING role and an
--    anon customer creates an order, the trigger's INSERT currently relies on the
--    public "system_can_insert_order_status_history" WITH CHECK(true) policy.
--    Removing it can make anon-initiated order creation fail at the trigger
--    UNLESS the trigger function is SECURITY DEFINER (owned by a role that
--    bypasses RLS) OR order creation now runs exclusively through the
--    service-role backend. Confirm one of those holds; if not, keep an INSERT
--    policy for the order-creation role instead of scoping to service_role.
DROP POLICY IF EXISTS "public_can_view_order_status_history"      ON public.order_status_history;
DROP POLICY IF EXISTS "system_can_insert_order_status_history"    ON public.order_status_history;
CREATE POLICY "Service role manages order_status_history"
    ON public.order_status_history
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3e. notifications — the three PERMISSIVE policies (public SELECT/INSERT/UPDATE
--     USING(true) / WITH CHECK(true)). The owner policies
--     ("Users view own notifications", "Users update own notifications",
--     auth.uid() = user_id) are KEPT.
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Anyone can create notifications" ON public.notifications;
DROP POLICY IF EXISTS "Service can insert notifications" ON public.notifications;
DROP POLICY IF EXISTS "Public can view notifications"    ON public.notifications;  -- name-variant, IF EXISTS no-op if absent
DROP POLICY IF EXISTS "Public can update notifications"  ON public.notifications;  -- name-variant, IF EXISTS no-op if absent
CREATE POLICY "Service role manages notifications"
    ON public.notifications
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3f. dispute_messages — includes is_internal notes; anon could read/forge.
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Anyone can view dispute messages"   ON public.dispute_messages;
DROP POLICY IF EXISTS "Anyone can insert dispute messages" ON public.dispute_messages;
DROP POLICY IF EXISTS "Anyone can update dispute messages"  ON public.dispute_messages;
CREATE POLICY "Service role manages dispute_messages"
    ON public.dispute_messages
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3g. ai_disputes — dispute records (the live dispute API table).
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "System update disputes" ON public.ai_disputes;
CREATE POLICY "Service role manages ai_disputes"
    ON public.ai_disputes
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3h. email_messages / email_threads / ai_escalations — support inbox content.
--     Prod has "Allow all" USING(true); repo also has a correctly-scoped
--     "Service role has full access to ..." policy which is KEPT.
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Allow all email_messages" ON public.email_messages;
DROP POLICY IF EXISTS "Allow all email_threads"  ON public.email_threads;
DROP POLICY IF EXISTS "Allow all ai_escalations" ON public.ai_escalations;
-- (No CREATE needed — the existing "Service role has full access to ..."
--  policies on these three tables already scope backend access correctly.
--  If a given environment lacks them, uncomment the block below.)
-- CREATE POLICY "Service role manages email_messages" ON public.email_messages
--     FOR ALL TO service_role USING (auth.role()='service_role') WITH CHECK (auth.role()='service_role');
-- CREATE POLICY "Service role manages email_threads"  ON public.email_threads
--     FOR ALL TO service_role USING (auth.role()='service_role') WITH CHECK (auth.role()='service_role');
-- CREATE POLICY "Service role manages ai_escalations" ON public.ai_escalations
--     FOR ALL TO service_role USING (auth.role()='service_role') WITH CHECK (auth.role()='service_role');

-- 3i. restaurant_websites — DROP with NO replacement (service-role-only).
--     The prod policy "Users can manage their own restaurant website" has
--     qual = true → every anon-key holder can read/write EVERY row. The table
--     CANNOT be owner-scoped: its columns are
--       id, restaurant_id(text), restaurant_name, blocks_data(jsonb),
--       published_url, is_published, created_at, updated_at, published_at, slug
--     — there is NO user_id / website_id / auth column to bind to auth.uid().
--     Grep of backend/ and frontend/src for "restaurant_websites" returns ZERO
--     code references (not anon, not service-role) — likely a dead/legacy table
--     (also no CREATE TABLE in the repo; prod-only). Dropping the policy leaves
--     RLS enabled with no policy = deny-all to anon/authenticated, while the
--     service-role backend still has full access (it bypasses RLS). Nothing
--     breaks. If this table is later revived, add a real ownership column first.
DROP POLICY IF EXISTS "Users can manage their own restaurant website"  ON public.restaurant_websites;
DROP POLICY IF EXISTS "Users can manage their own restaurant websites" ON public.restaurant_websites;  -- plural name-variant
DROP POLICY IF EXISTS "Users can manage their own website"             ON public.restaurant_websites;  -- name-variant

-- 3j. order_verifications — "Service can manage order verifications" FOR ALL
--     WITH CHECK(true). Keep the user-view policy.
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Service can manage order verifications" ON public.order_verifications;
CREATE POLICY "Service role manages order_verifications"
    ON public.order_verifications
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3k. ai_chat_settings — "Service can manage AI chat settings" FOR ALL
--     WITH CHECK(true). Keep the two owner policies (view/manage own).
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Service can manage AI chat settings" ON public.ai_chat_settings;
CREATE POLICY "Service role manages ai_chat_settings"
    ON public.ai_chat_settings
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3l. dispute_fraud_patterns — flagged public; exact prod policy name unknown
--     (no CREATE POLICY in repo). Targeted dynamic drop of any permissive
--     public policy on THIS TABLE ONLY (roles overlap public/anon/authenticated
--     AND USING/CHECK is literally `true`), then assert the service_role policy.
--     This precise predicate leaves owner (auth.uid()) and conditioned policies
--     intact. [FRONTEND] no direct anon access found (grep clean).
DO $$
DECLARE p record;
BEGIN
    FOR p IN
        SELECT policyname
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'dispute_fraud_patterns'
          AND (qual = 'true' OR with_check = 'true')
          AND roles && ARRAY['public','anon','authenticated']::name[]
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.dispute_fraud_patterns;', p.policyname);
    END LOOP;
END $$;
CREATE POLICY "Service role manages dispute_fraud_patterns"
    ON public.dispute_fraud_patterns
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3m. restaurant_health — "System manage restaurant health" FOR ALL USING(true).
--     Keep "Users view own restaurant health" (auth.uid() = user_id).
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "System manage restaurant health" ON public.restaurant_health;
CREATE POLICY "Service role manages restaurant_health"
    ON public.restaurant_health
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3n. restaurant_penalties — "Service can manage penalties" FOR ALL WITH CHECK(true).
--     Keep "Users view own penalties" (auth.uid() = user_id).
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Service can manage penalties" ON public.restaurant_penalties;
CREATE POLICY "Service role manages restaurant_penalties"
    ON public.restaurant_penalties
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3o. referral_codes / referral_history — "Service can manage ..." FOR ALL
--     WITH CHECK(true). Keep "Users view own referral code" (auth.uid()=user_id).
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Service can manage referral codes" ON public.referral_codes;
CREATE POLICY "Service role manages referral_codes"
    ON public.referral_codes
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service can manage referral history" ON public.referral_history;
DROP POLICY IF EXISTS "System manage referral history"      ON public.referral_history;  -- name-variant
CREATE POLICY "Service role manages referral_history"
    ON public.referral_history
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3p. sla_breaches — "Service can insert SLA breaches" INSERT WITH CHECK(true).
--     Keep "Users view own SLA breaches" (auth.uid() = user_id).
-- [FRONTEND] no direct anon access found (grep clean).
DROP POLICY IF EXISTS "Service can insert SLA breaches" ON public.sla_breaches;
CREATE POLICY "Service role manages sla_breaches"
    ON public.sla_breaches
    FOR ALL
    TO service_role
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- =============================================================================
-- SECTION 4 — storage.objects: menu-images bucket public ALL -> public SELECT
--   The public bucket must stay publicly READABLE (menu photos on the live
--   customer site) but must NOT be publicly writable/deletable by anon.
-- [FRONTEND] AssetsManager uploads go through an authenticated/backend path;
--   customer sites only READ menu images. VERIFY the exact policy name against
--   storage.objects (names there are free-form).
-- =============================================================================
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
CREATE POLICY "menu-images public read"
    ON storage.objects
    FOR SELECT
    TO public
    USING (bucket_id = 'menu-images');
-- NOTE: "Public Access" is a common default name that may exist on OTHER buckets
--   too. If your prod "Public Access" policy was bucket-scoped differently,
--   reconcile against: SELECT * FROM pg_policies WHERE tablename='objects';
--   The website-read and chat-image object policies are intentionally KEPT.

COMMIT;

-- =============================================================================
-- POST-APPLY VERIFICATION (run manually; not part of the transaction)
--   Should return ZERO rows for the tables hardened above. Any row = a still-open
--   public USING(true)/WITH CHECK(true) policy (likely a prod name this migration
--   did not match — reconcile and re-drop).
-- =============================================================================
-- SELECT tablename, policyname, cmd, roles, qual, with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
--   AND (qual = 'true' OR with_check = 'true')
--   AND roles && ARRAY['public','anon','authenticated']::name[]
--   AND tablename IN (
--     'subscriptions','delivery_orders','bina_credits','promo_config',
--     'promo_redemptions','chat_messages','chat_conversations','order_items',
--     'order_status_history','notifications','dispute_messages','ai_disputes',
--     'email_messages','email_threads','ai_escalations','restaurant_websites',
--     'order_verifications','ai_chat_settings','dispute_fraud_patterns',
--     'restaurant_health','restaurant_penalties','referral_codes',
--     'referral_history','sla_breaches'
--   )
-- ORDER BY tablename, policyname;

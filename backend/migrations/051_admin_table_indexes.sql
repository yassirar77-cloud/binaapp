-- =============================================================================
-- Migration 051: indexes for admin-side AI/credit tables
-- =============================================================================
-- Perf audit follow-up, RECONCILED AGAINST LIVE PROD INDEXES on 2026-07-05.
--
-- These tables have no CREATE TABLE in this repo — they were created directly
-- in prod, together with a set of ad-hoc indexes under a different naming
-- convention. The original version of this migration proposed seven indexes
-- derived from backend query patterns; checking prod's pg_indexes showed five
-- of them were already covered (or blocked by a missing column), so creating
-- them would only have added duplicate indexes. Only the two statements below
-- add real coverage. They were applied to prod manually on 2026-07-05; the
-- guards keep this file a safe no-op everywhere else.
--
-- Query patterns covered (from backend code):
--   ai_disputes.order_id            .eq(order_id)                [admin_dashboard.py]
--   credit_transactions(type,       .eq(type) + .gt(created_at)  [ai_chatbot_service.py
--                       created_at)                               admin_dashboard.py]
--
-- NOT created — already covered by pre-existing prod indexes:
--   idx_ai_disputes_status          → prod: idx_ai_disputes_status (status)
--   idx_ai_disputes_created_at      → prod: idx_ai_disputes_created (created_at)
--                                     (plain btree; scans backwards for DESC)
--   idx_credit_transactions_user_id → prod: idx_credit_transactions_user (user_id)
--   idx_bina_credits_user_id        → prod: bina_credits_user_id_key UNIQUE (user_id)
--
-- NOT created — blocked by schema reality:
--   idx_credit_transactions_status_expires → credit_transactions has NO status
--     column in prod. The code path that filters on it (check_credit_expiry in
--     ai_proactive_monitor.py) errors on every run and is tracked as a separate
--     bug; prod's partial index idx_credit_transactions_expires
--     (expires_at WHERE expires_at IS NOT NULL) already serves the
--     .lt(expires_at) side. Revisit this index if/when the status column is
--     added as part of that fix.
-- =============================================================================

DO $$
BEGIN
    -- ---------------------------------------------------------------- ai_disputes
    IF to_regclass('public.ai_disputes') IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'ai_disputes'
                     AND column_name = 'order_id') THEN
            CREATE INDEX IF NOT EXISTS idx_ai_disputes_order_id
                ON public.ai_disputes (order_id);
        END IF;
    END IF;

    -- -------------------------------------------------------- credit_transactions
    IF to_regclass('public.credit_transactions') IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'credit_transactions'
                     AND column_name = 'type')
           AND EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'credit_transactions'
                     AND column_name = 'created_at') THEN
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_type_created
                ON public.credit_transactions (type, created_at DESC);
        END IF;
    END IF;
END $$;

-- =============================================================================
-- Migration 051: indexes for admin-side AI/credit tables
-- =============================================================================
-- Perf audit follow-up. The admin dashboard and AI support services filter
-- ai_disputes / credit_transactions / bina_credits on columns that have no
-- index. These tables have no CREATE TABLE in this repo (created directly in
-- prod), so every statement is guarded: it only runs if the table AND the
-- filtered column actually exist. Safe to run on any environment; a schema
-- without these tables is a no-op.
--
-- Query patterns covered (from backend code):
--   ai_disputes:         .eq(status), .gt(created_at) + order created_at desc,
--                        .eq(order_id)                      [admin_dashboard.py]
--   credit_transactions: .eq(user_id), .eq(type)+.gt(created_at),
--                        .eq(status)+.lt(expires_at)        [admin_dashboard.py,
--                                                            ai_chatbot_service.py,
--                                                            ai_proactive_monitor.py]
--   bina_credits:        .eq(user_id)  (wallet lookup on every credit award)
-- =============================================================================

DO $$
BEGIN
    -- ---------------------------------------------------------------- ai_disputes
    IF to_regclass('public.ai_disputes') IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'ai_disputes'
                     AND column_name = 'status') THEN
            CREATE INDEX IF NOT EXISTS idx_ai_disputes_status
                ON public.ai_disputes (status);
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'ai_disputes'
                     AND column_name = 'created_at') THEN
            CREATE INDEX IF NOT EXISTS idx_ai_disputes_created_at
                ON public.ai_disputes (created_at DESC);
        END IF;

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
                     AND column_name = 'user_id') THEN
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id
                ON public.credit_transactions (user_id);
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'credit_transactions'
                     AND column_name = 'type')
           AND EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'credit_transactions'
                     AND column_name = 'created_at') THEN
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_type_created
                ON public.credit_transactions (type, created_at DESC);
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'credit_transactions'
                     AND column_name = 'status')
           AND EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'credit_transactions'
                     AND column_name = 'expires_at') THEN
            CREATE INDEX IF NOT EXISTS idx_credit_transactions_status_expires
                ON public.credit_transactions (status, expires_at);
        END IF;
    END IF;

    -- ---------------------------------------------------------------- bina_credits
    IF to_regclass('public.bina_credits') IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'bina_credits'
                     AND column_name = 'user_id') THEN
            CREATE INDEX IF NOT EXISTS idx_bina_credits_user_id
                ON public.bina_credits (user_id);
        END IF;
    END IF;
END $$;

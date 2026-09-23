-- Migration 059: Revoke client EXECUTE on SECURITY DEFINER functions
-- Supabase advisors: anon/authenticated_security_definer_function_executable.
-- These functions run with owner rights and several take p_user_id as a plain
-- argument, so anyone holding the public anon key could call them via
-- /rest/v1/rpc/* on behalf of any user (e.g. upgrade_subscription,
-- redeem_promo_code, cancel_delivery_order). They are only called by the
-- backend with the service_role key, and trigger functions do not need
-- EXECUTE for the trigger to fire.
-- The st_estimatedextent(...) functions are PostGIS-owned (supabase_admin)
-- and cannot be changed from the postgres role.
-- Applied to production 2026-09-23.

DO $$
DECLARE
    fn text;
BEGIN
    FOREACH fn IN ARRAY ARRAY[
        'public.cancel_delivery_order(uuid,uuid,text)',
        'public.get_promo_status(uuid)',
        'public.handle_new_user()',
        'public.initialize_user_subscription()',
        'public.insert_delivery_zone(uuid,uuid,text,text,integer,integer,text,jsonb,integer,integer,text,boolean,integer,integer)',
        'public.is_subscription_locked(uuid)',
        'public.is_website_locked(uuid)',
        'public.log_order_status_change()',
        'public.reassign_order_rider(uuid,uuid,uuid)',
        'public.redeem_promo_code(uuid,text)',
        'public.reset_monthly_usage()',
        'public.sync_subscription_plan_id()',
        'public.update_delivery_zone(uuid,uuid,text,text,integer,integer,text,jsonb,integer,integer,text,boolean,integer,integer)',
        'public.update_website_location(uuid,uuid,double precision,double precision)',
        'public.upgrade_subscription(uuid,character varying,numeric)',
        'public.avrc_increment_rate_limit(uuid,text,timestamp with time zone)',
        'public.avrc_minutes_used(uuid,timestamp with time zone)'
    ]
    LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC, anon, authenticated', fn);
        EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', fn);
    END LOOP;
END $$;


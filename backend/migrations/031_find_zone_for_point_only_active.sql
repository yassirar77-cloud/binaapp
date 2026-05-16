-- =====================================================
-- 031_find_zone_for_point_only_active.sql
--
-- Codifies the 4-param signature of find_zone_for_point that the FastAPI
-- code in backend/app/api/v1/endpoints/delivery_zones.py already calls
-- (see test_point() — it passes p_only_active).
--
-- Migration 026 originally created a 3-param version. Comments in
-- 028_zones_explicit_user_id.sql reference a "migration 026a" that added
-- p_only_active, but that file does not exist in the repo — the deployed
-- function was patched out-of-band. This file makes the repo and prod
-- agree so future deploys / fresh DBs don't regress to the 3-arg version.
--
-- The live deployed function (confirmed via pg_get_functiondef before
-- writing this migration) returns 6 columns:
--   id, name, fee_cents, min_order_cents, color, active
-- This migration is PURELY ADDITIVE: it preserves all 6 columns and adds
-- a 7th (estimated_delivery_min) so the public coverage endpoint and the
-- legacy create_order path can stamp delivery_orders.estimated_delivery_time
-- without a second DB roundtrip. Nothing currently reading the function
-- will break — existing callers ignore extra columns.
--
-- IMPORTANT: Before applying, re-run
--   select pg_get_functiondef('public.find_zone_for_point'::regproc);
-- to confirm the live signature still matches what's documented above.
-- If the live function differs in any other way (extra columns,
-- different default, etc.), reconcile BEFORE applying — this script
-- drops and recreates.
-- =====================================================

-- Drop both possible existing overloads so the recreate is unambiguous.
drop function if exists public.find_zone_for_point(uuid, double precision, double precision);
drop function if exists public.find_zone_for_point(uuid, double precision, double precision, boolean);

create or replace function public.find_zone_for_point(
  p_website_id uuid,
  p_lat double precision,
  p_lng double precision,
  p_only_active boolean default true
)
returns table (
  id uuid,
  name text,
  fee_cents integer,
  min_order_cents integer,
  color text,
  active boolean,
  estimated_delivery_min integer
)
language sql stable as $$
  select
    id,
    name,
    fee_cents,
    min_order_cents,
    color,
    active,
    estimated_delivery_min
  from public.delivery_zones
  where website_id = p_website_id
    and (not p_only_active or active = true)
    and ST_Covers(polygon, ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography)
  order by ST_Area(polygon::geography) asc
  limit 1;
$$;

grant execute on function public.find_zone_for_point(uuid, double precision, double precision, boolean)
  to anon, authenticated, service_role;

-- =====================================================
-- 027_zones_rings.sql
-- Adds outlet location to websites + ring metadata to delivery_zones.
--
-- The polygon column stays — a ring is a generated 64-vertex polygon
-- (donut: outer ring minus inner ring) so all existing RPCs keep working.
-- The new inner_radius_m and outer_radius_m columns are metadata that
-- let the UI reconstruct ring controls without re-deriving from polygon.
-- =====================================================

-- Outlet location columns on websites
alter table public.websites
  add column if not exists lat double precision,
  add column if not exists lng double precision;

comment on column public.websites.lat is 'Outlet latitude in WGS84. Set by owner via penghantaran page or auto-geocoded from location_address.';
comment on column public.websites.lng is 'Outlet longitude in WGS84.';

-- Ring metadata on delivery_zones
alter table public.delivery_zones
  add column if not exists inner_radius_m integer check (inner_radius_m >= 0),
  add column if not exists outer_radius_m integer check (outer_radius_m > 0);

comment on column public.delivery_zones.inner_radius_m is 'Inner radius in meters from outlet center. 0 for innermost ring. NULL for legacy polygon zones (none should exist after migration 026a).';
comment on column public.delivery_zones.outer_radius_m is 'Outer radius in meters from outlet center. Must be > inner_radius_m. NULL for legacy polygon zones.';

-- Validation: inner < outer when both set
alter table public.delivery_zones
  drop constraint if exists delivery_zones_radius_check;

alter table public.delivery_zones
  add constraint delivery_zones_radius_check
  check (
    (inner_radius_m is null and outer_radius_m is null) or
    (inner_radius_m is not null and outer_radius_m is not null and outer_radius_m > inner_radius_m)
  );

-- =====================================================
-- update_website_location RPC — security definer, owner check
-- =====================================================
create or replace function public.update_website_location(
  p_website_id uuid,
  p_lat double precision,
  p_lng double precision
) returns void language plpgsql security definer as $$
begin
  if not exists (
    select 1 from public.websites
    where id = p_website_id and user_id = auth.uid()
  ) then
    raise exception 'forbidden';
  end if;

  if p_lat is null or p_lng is null then
    raise exception 'lat and lng are required';
  end if;

  if p_lat < -90 or p_lat > 90 or p_lng < -180 or p_lng > 180 then
    raise exception 'lat/lng out of range';
  end if;

  update public.websites
    set lat = p_lat, lng = p_lng, updated_at = now()
  where id = p_website_id;
end $$;

grant execute on function public.update_website_location(uuid, double precision, double precision) to authenticated;

-- =====================================================
-- Update insert_delivery_zone + update_delivery_zone to accept ring metadata
-- =====================================================
drop function if exists public.insert_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean);

create or replace function public.insert_delivery_zone(
  p_website_id uuid,
  p_name text,
  p_color text,
  p_fee_cents integer,
  p_min_order_cents integer,
  p_polygon_geojson text,
  p_schedule_json jsonb,
  p_estimated_delivery_min integer,
  p_max_simultaneous_orders integer,
  p_customer_notes text,
  p_active boolean,
  p_inner_radius_m integer,
  p_outer_radius_m integer
) returns uuid language plpgsql security definer as $$
declare v_id uuid;
begin
  if not exists (
    select 1 from public.websites
    where id = p_website_id and user_id = auth.uid()
  ) then
    raise exception 'forbidden';
  end if;

  insert into public.delivery_zones(
    website_id, name, color,
    fee_cents, min_order_cents, polygon, schedule_json,
    estimated_delivery_min, max_simultaneous_orders, customer_notes, active,
    inner_radius_m, outer_radius_m
  ) values (
    p_website_id, p_name, p_color,
    p_fee_cents, p_min_order_cents,
    ST_GeomFromGeoJSON(p_polygon_geojson)::geography,
    p_schedule_json, p_estimated_delivery_min, p_max_simultaneous_orders,
    p_customer_notes, p_active,
    p_inner_radius_m, p_outer_radius_m
  ) returning id into v_id;

  return v_id;
end $$;

grant execute on function public.insert_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean, integer, integer) to authenticated;

drop function if exists public.update_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean);

create or replace function public.update_delivery_zone(
  p_zone_id uuid,
  p_name text,
  p_color text,
  p_fee_cents integer,
  p_min_order_cents integer,
  p_polygon_geojson text,
  p_schedule_json jsonb,
  p_estimated_delivery_min integer,
  p_max_simultaneous_orders integer,
  p_customer_notes text,
  p_active boolean,
  p_inner_radius_m integer,
  p_outer_radius_m integer
) returns uuid language plpgsql security definer as $$
declare v_owner uuid;
begin
  select w.user_id into v_owner
  from public.delivery_zones z
  join public.websites w on w.id = z.website_id
  where z.id = p_zone_id;

  if v_owner is null or v_owner <> auth.uid() then
    raise exception 'forbidden';
  end if;

  update public.delivery_zones set
    name                    = coalesce(p_name, name),
    color                   = coalesce(p_color, color),
    fee_cents               = coalesce(p_fee_cents, fee_cents),
    min_order_cents         = coalesce(p_min_order_cents, min_order_cents),
    polygon                 = case
                                when p_polygon_geojson is null then polygon
                                else ST_GeomFromGeoJSON(p_polygon_geojson)::geography
                              end,
    schedule_json           = coalesce(p_schedule_json, schedule_json),
    estimated_delivery_min  = coalesce(p_estimated_delivery_min, estimated_delivery_min),
    max_simultaneous_orders = coalesce(p_max_simultaneous_orders, max_simultaneous_orders),
    customer_notes          = coalesce(p_customer_notes, customer_notes),
    active                  = coalesce(p_active, active),
    inner_radius_m          = coalesce(p_inner_radius_m, inner_radius_m),
    outer_radius_m          = coalesce(p_outer_radius_m, outer_radius_m)
  where id = p_zone_id;

  return p_zone_id;
end $$;

grant execute on function public.update_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean, integer, integer) to authenticated;

-- =====================================================
-- Update list_delivery_zones to return ring metadata
-- =====================================================
drop function if exists public.list_delivery_zones(uuid);

create or replace function public.list_delivery_zones(p_website_id uuid)
returns table (
  id uuid,
  website_id uuid,
  name text,
  color text,
  fee_cents integer,
  min_order_cents integer,
  polygon_geojson jsonb,
  schedule_json jsonb,
  estimated_delivery_min integer,
  max_simultaneous_orders integer,
  customer_notes text,
  active boolean,
  area_m2 double precision,
  inner_radius_m integer,
  outer_radius_m integer,
  created_at timestamptz,
  updated_at timestamptz
) language sql stable as $$
  select
    z.id, z.website_id, z.name, z.color,
    z.fee_cents, z.min_order_cents,
    ST_AsGeoJSON(z.polygon)::jsonb as polygon_geojson,
    z.schedule_json,
    z.estimated_delivery_min, z.max_simultaneous_orders,
    z.customer_notes, z.active,
    ST_Area(z.polygon::geography) as area_m2,
    z.inner_radius_m, z.outer_radius_m,
    z.created_at, z.updated_at
  from public.delivery_zones z
  where z.website_id = p_website_id
  order by coalesce(z.outer_radius_m, 0) asc, z.created_at asc;
$$;

grant execute on function public.list_delivery_zones(uuid) to authenticated, anon;

-- =====================================================
-- Verification (run after applying)
-- =====================================================
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'websites' AND column_name IN ('lat','lng');  -- expect 2 rows
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'delivery_zones' AND column_name IN ('inner_radius_m','outer_radius_m');  -- expect 2 rows
-- SELECT proname FROM pg_proc WHERE proname IN ('update_website_location','insert_delivery_zone','update_delivery_zone','list_delivery_zones');  -- expect 4 rows

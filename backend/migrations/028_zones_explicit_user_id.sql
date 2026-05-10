-- =====================================================
-- 028_zones_explicit_user_id.sql
-- The custom JWT system means auth.uid() returns NULL inside RPCs
-- when called via the service-role client. Replace it with an explicit
-- p_user_id parameter that the FastAPI layer extracts from the verified
-- JWT and passes through.
--
-- list_delivery_zones and find_zone_for_point are unchanged — ownership
-- is verified at the FastAPI layer before they're invoked.
-- =====================================================

drop function if exists public.update_website_location(uuid, double precision, double precision);

create or replace function public.update_website_location(
  p_user_id uuid,
  p_website_id uuid,
  p_lat double precision,
  p_lng double precision
) returns void language plpgsql security definer as $$
begin
  if not exists (
    select 1 from public.websites
    where id = p_website_id and user_id = p_user_id
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

grant execute on function public.update_website_location(uuid, uuid, double precision, double precision) to authenticated, service_role;

drop function if exists public.insert_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean, integer, integer);

create or replace function public.insert_delivery_zone(
  p_user_id uuid,
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
    where id = p_website_id and user_id = p_user_id
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

grant execute on function public.insert_delivery_zone(uuid, uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean, integer, integer) to authenticated, service_role;

drop function if exists public.update_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean, integer, integer);

create or replace function public.update_delivery_zone(
  p_user_id uuid,
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

  if v_owner is null or v_owner <> p_user_id then
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

grant execute on function public.update_delivery_zone(uuid, uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean, integer, integer) to authenticated, service_role;

-- list_delivery_zones unchanged — ownership verified at FastAPI layer.
-- find_zone_for_point unchanged (from migration 026a).

-- =====================================================
-- Verification
-- =====================================================
-- SELECT proname, pronargs FROM pg_proc
-- WHERE proname IN ('update_website_location','insert_delivery_zone','update_delivery_zone')
-- ORDER BY proname;
-- expect: insert_delivery_zone | 14, update_delivery_zone | 14, update_website_location | 4

-- =====================================================
-- 053_penghantar_live_rpc_perf.sql
--
-- Performance fix for the two Penghantar Live list RPCs from migration 029.
--
-- Both functions built their CTEs over the ENTIRE delivery_orders /
-- order_items tables before joining down to one website:
--   * list_riders_with_orders: active_orders + today_stats scanned all
--     orders for every website on the platform.
--   * list_active_orders: items_agg aggregated every order_items row in the
--     database.
-- These run every 15-60s per open dashboard, so push p_website_id into the
-- CTEs. Signatures and result shapes are unchanged — this is a drop-in
-- CREATE OR REPLACE, no callers need changes.
-- =====================================================

create or replace function public.list_riders_with_orders(p_website_id uuid)
returns table (
  id uuid,
  name text,
  phone text,
  vehicle_plate text,
  vehicle_type text,
  vehicle_model text,
  is_active boolean,
  is_online boolean,
  current_latitude double precision,
  current_longitude double precision,
  last_location_update timestamptz,
  active_order_id uuid,
  active_order_number text,
  active_order_eta_at timestamptz,
  active_order_status text,
  today_deliveries integer
) language sql stable as $$
  with active_orders as (
    select
      o.rider_id,
      o.id as order_id,
      o.order_number,
      o.estimated_delivery_time,
      o.created_at,
      o.status,
      row_number() over (partition by o.rider_id order by o.created_at desc) as rn
    from public.delivery_orders o
    where o.website_id = p_website_id
      and o.rider_id is not null
      and o.status in ('confirmed', 'preparing', 'ready', 'picked_up', 'delivering')
  ),
  today_stats as (
    select
      rider_id,
      count(*)::int as deliveries
    from public.delivery_orders
    where website_id = p_website_id
      and status in ('delivered', 'completed')
      and delivered_at >= (now() at time zone 'Asia/Kuala_Lumpur')::date
      and rider_id is not null
    group by rider_id
  )
  select
    r.id,
    r.name,
    r.phone,
    r.vehicle_plate,
    r.vehicle_type,
    r.vehicle_model,
    r.is_active,
    r.is_online,
    r.current_latitude::double precision,
    r.current_longitude::double precision,
    r.last_location_update,
    ao.order_id,
    ao.order_number,
    case when ao.estimated_delivery_time is not null
      then ao.created_at + (ao.estimated_delivery_time || ' minutes')::interval
      else null
    end as active_order_eta_at,
    ao.status,
    coalesce(ts.deliveries, 0)::int
  from public.riders r
  left join active_orders ao on ao.rider_id = r.id and ao.rn = 1
  left join today_stats ts on ts.rider_id = r.id
  where r.website_id = p_website_id
  order by
    case
      when r.is_online and r.last_location_update > now() - interval '5 min' then 0
      when r.is_online then 1
      else 2
    end,
    r.name;
$$;

grant execute on function public.list_riders_with_orders(uuid) to authenticated, service_role;

create or replace function public.list_active_orders(p_website_id uuid)
returns table (
  id uuid,
  order_number text,
  customer_name text,
  customer_phone text,
  delivery_address text,
  delivery_latitude double precision,
  delivery_longitude double precision,
  items jsonb,
  subtotal numeric,
  delivery_fee numeric,
  total_amount numeric,
  status text,
  created_at timestamptz,
  picked_up_at timestamptz,
  estimated_delivery_time integer,
  eta_at timestamptz,
  rider_id uuid,
  rider_name text,
  rider_phone text,
  rider_vehicle_plate text,
  rider_current_latitude double precision,
  rider_current_longitude double precision,
  rider_last_location_update timestamptz,
  rider_is_online boolean,
  delivery_zone_id uuid,
  zone_name text,
  zone_color text,
  zone_outer_radius_m integer
) language sql stable as $$
  with items_agg as (
    select
      oi.order_id,
      jsonb_agg(
        jsonb_build_object(
          'id', oi.id,
          'menu_item_id', oi.menu_item_id,
          'item_name', oi.item_name,
          'quantity', oi.quantity,
          'unit_price', oi.unit_price,
          'total_price', oi.total_price,
          'options', oi.options,
          'notes', oi.notes
        )
        order by oi.id
      ) as items
    from public.order_items oi
    where oi.order_id in (
      select o.id from public.delivery_orders o
      where o.website_id = p_website_id
        and o.status in ('pending', 'confirmed', 'preparing', 'ready', 'picked_up', 'delivering')
    )
    group by oi.order_id
  )
  select
    o.id,
    o.order_number,
    o.customer_name,
    o.customer_phone,
    o.delivery_address,
    o.delivery_latitude::double precision,
    o.delivery_longitude::double precision,
    coalesce(ia.items, '[]'::jsonb) as items,
    o.subtotal,
    o.delivery_fee,
    o.total_amount,
    o.status,
    o.created_at,
    o.picked_up_at,
    o.estimated_delivery_time,
    case when o.estimated_delivery_time is not null
      then o.created_at + (o.estimated_delivery_time || ' minutes')::interval
      else null
    end as eta_at,
    o.rider_id,
    r.name as rider_name,
    r.phone as rider_phone,
    r.vehicle_plate as rider_vehicle_plate,
    r.current_latitude::double precision as rider_current_latitude,
    r.current_longitude::double precision as rider_current_longitude,
    r.last_location_update as rider_last_location_update,
    r.is_online as rider_is_online,
    o.delivery_zone_id,
    z.name as zone_name,
    z.color as zone_color,
    z.outer_radius_m as zone_outer_radius_m
  from public.delivery_orders o
  left join public.riders r on r.id = o.rider_id
  left join public.delivery_zones z on z.id = o.delivery_zone_id
  left join items_agg ia on ia.order_id = o.id
  where o.website_id = p_website_id
    and o.status in ('pending', 'confirmed', 'preparing', 'ready', 'picked_up', 'delivering')
  order by o.created_at desc;
$$;

grant execute on function public.list_active_orders(uuid) to authenticated, service_role;

-- =====================================================
-- Verification (run after applying)
-- =====================================================
-- SELECT proname FROM pg_proc
--   WHERE proname IN ('list_riders_with_orders', 'list_active_orders');
-- -- expect 2 rows; EXPLAIN ANALYZE both with a real website id and confirm
-- -- delivery_orders is filtered by website_id inside every CTE.

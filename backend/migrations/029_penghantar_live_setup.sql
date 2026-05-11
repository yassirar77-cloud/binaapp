-- =====================================================
-- 029_penghantar_live_setup.sql
--
-- Backend setup for /dashboard/penghantar-live (real-time rider monitoring).
--
-- This migration does NOT add GPS columns to riders — those already exist as
--   current_latitude, current_longitude, last_location_update
-- (migration 002). It only adds:
--   1. cancellation_reason + cancelled_by_user_id on delivery_orders
--   2. Index on riders for the live query
--   3. Supabase Realtime publication for riders
--   4. Four RPCs used by the live page
--
-- All RPCs use the REAL column names. Status filter uses canonical English
-- values only: pending, confirmed, preparing, ready, picked_up, delivering,
-- delivered, completed, cancelled.
-- =====================================================

-- =====================================================
-- 1. Schema additions on delivery_orders
-- =====================================================
alter table public.delivery_orders
  add column if not exists cancellation_reason text,
  add column if not exists cancelled_by_user_id uuid references auth.users(id);

comment on column public.delivery_orders.cancellation_reason is
  'Free-text reason supplied by the outlet owner when cancelling. Set by cancel_delivery_order RPC. NULL for non-cancelled orders.';
comment on column public.delivery_orders.cancelled_by_user_id is
  'auth.users id of the owner who cancelled the order. Set by cancel_delivery_order RPC.';

-- =====================================================
-- 2. Index for live rider lookup
-- =====================================================
create index if not exists riders_website_id_active_idx
  on public.riders(website_id)
  where last_location_update is not null;

-- =====================================================
-- 3. Supabase Realtime publication
-- =====================================================
-- Adding a table that is already in the publication raises duplicate_object,
-- so wrap in DO block for idempotency.
do $$
begin
  alter publication supabase_realtime add table public.riders;
exception
  when duplicate_object then null;
end $$;

-- =====================================================
-- 4. RPC: list_riders_with_orders
-- Returns each rider for a website with their (most recent) active order info
-- and today's delivered count. Service-role-keyed; FastAPI verifies ownership.
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
    where o.rider_id is not null
      and o.status in ('confirmed', 'preparing', 'ready', 'picked_up', 'delivering')
  ),
  today_stats as (
    select
      rider_id,
      count(*)::int as deliveries
    from public.delivery_orders
    where status in ('delivered', 'completed')
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

-- =====================================================
-- 5. RPC: list_active_orders
-- Returns active orders with denormalized rider + zone info, plus items
-- aggregated from order_items table.
-- =====================================================
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
-- 6. RPC: reassign_order_rider
-- Reassigns (or unassigns when p_new_rider_id is null) the rider on an active
-- order. Verifies ownership and that the new rider belongs to the same website.
-- =====================================================
create or replace function public.reassign_order_rider(
  p_user_id uuid,
  p_order_id uuid,
  p_new_rider_id uuid
) returns void language plpgsql security definer as $$
declare
  v_website_id uuid;
  v_owner uuid;
  v_status text;
begin
  select o.website_id, w.user_id, o.status
    into v_website_id, v_owner, v_status
  from public.delivery_orders o
  join public.websites w on w.id = o.website_id
  where o.id = p_order_id;

  if v_owner is null or v_owner <> p_user_id then
    raise exception 'forbidden';
  end if;

  if v_status in ('delivered', 'completed', 'cancelled') then
    raise exception 'cannot reassign rider on order in status: %', v_status;
  end if;

  if p_new_rider_id is not null then
    if not exists (
      select 1 from public.riders
      where id = p_new_rider_id and website_id = v_website_id
    ) then
      raise exception 'rider not in this outlet';
    end if;
  end if;

  update public.delivery_orders
  set rider_id = p_new_rider_id
  where id = p_order_id;
end $$;

grant execute on function public.reassign_order_rider(uuid, uuid, uuid) to authenticated, service_role;

-- =====================================================
-- 7. RPC: cancel_delivery_order
-- Status change only — refund/payment reversal is handled manually by the owner.
-- Refuses to cancel orders already delivered/completed/cancelled.
-- =====================================================
create or replace function public.cancel_delivery_order(
  p_user_id uuid,
  p_order_id uuid,
  p_reason text
) returns void language plpgsql security definer as $$
declare
  v_owner uuid;
  v_status text;
begin
  select w.user_id, o.status into v_owner, v_status
  from public.delivery_orders o
  join public.websites w on w.id = o.website_id
  where o.id = p_order_id;

  if v_owner is null or v_owner <> p_user_id then
    raise exception 'forbidden';
  end if;

  if v_status in ('delivered', 'completed', 'cancelled') then
    raise exception 'cannot cancel order in status: %', v_status;
  end if;

  if p_reason is null or length(btrim(p_reason)) < 10 then
    raise exception 'cancellation reason must be at least 10 characters';
  end if;

  update public.delivery_orders
  set
    status = 'cancelled',
    cancelled_at = now(),
    cancellation_reason = p_reason,
    cancelled_by_user_id = p_user_id
  where id = p_order_id;
end $$;

grant execute on function public.cancel_delivery_order(uuid, uuid, text) to authenticated, service_role;

-- =====================================================
-- Verification queries (run after applying)
-- =====================================================
-- 1. New columns on delivery_orders:
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'delivery_orders'
--     AND column_name IN ('cancellation_reason', 'cancelled_by_user_id');
-- -- expect 2 rows
--
-- 2. RPCs registered:
-- SELECT proname FROM pg_proc
--   WHERE proname IN ('list_riders_with_orders', 'list_active_orders',
--                     'reassign_order_rider', 'cancel_delivery_order');
-- -- expect 4 rows
--
-- 3. Realtime publication includes riders:
-- SELECT tablename FROM pg_publication_tables
--   WHERE pubname = 'supabase_realtime' AND tablename = 'riders';
-- -- expect 1 row
--
-- 4. Index exists:
-- SELECT indexname FROM pg_indexes
--   WHERE tablename = 'riders' AND indexname = 'riders_website_id_active_idx';
-- -- expect 1 row

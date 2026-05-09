-- =====================================================
-- 026_delivery_zones_postgis.sql
-- Owner-side delivery zone management (Urus Penghantaran)
--
-- Adds PostGIS-backed polygon support, schedule, and richer
-- metadata to delivery_zones. This migration replaces the
-- legacy delivery_zones definition from 002_delivery_system.sql.
--
-- Notes
-- - Zones are per-website (binaapp uses websites, not outlets).
-- - websites.user_id is the owner used for RLS.
-- - Existing rows in delivery_zones are dropped — the previous
--   schema (zone_polygon JSONB) is incompatible with the new
--   geography(Polygon, 4326) column and the legacy data is not
--   yet in production use for the owner UI.
-- =====================================================

create extension if not exists postgis;

-- Drop dependent objects from the old table (safe if missing)
drop trigger if exists update_delivery_zones_updated_at on public.delivery_zones;
drop policy if exists "Users can view own delivery zones" on public.delivery_zones;
drop policy if exists "Users can manage own delivery zones" on public.delivery_zones;
drop policy if exists "Public can view active zones" on public.delivery_zones;

-- The legacy table is referenced by orders.delivery_zone_id; that
-- FK is recreated after we recreate the table.
alter table if exists public.orders
  drop constraint if exists orders_delivery_zone_id_fkey;

drop table if exists public.delivery_zones cascade;

create table public.delivery_zones (
  id uuid primary key default gen_random_uuid(),
  website_id uuid not null references public.websites(id) on delete cascade,
  name text not null,
  color text not null default '#C7FF3D',
  fee_cents integer not null default 500 check (fee_cents >= 0),
  min_order_cents integer not null default 2000 check (min_order_cents >= 0),
  polygon geography(Polygon, 4326) not null,
  schedule_json jsonb not null default '{
    "mon": {"open": "10:00", "close": "22:00", "active": true},
    "tue": {"open": "10:00", "close": "22:00", "active": true},
    "wed": {"open": "10:00", "close": "22:00", "active": true},
    "thu": {"open": "10:00", "close": "22:00", "active": true},
    "fri": {"open": "10:00", "close": "22:00", "active": true},
    "sat": {"open": "10:00", "close": "22:00", "active": true},
    "sun": {"open": "10:00", "close": "22:00", "active": true}
  }'::jsonb,
  estimated_delivery_min integer default 30,
  max_simultaneous_orders integer default 10,
  customer_notes text,
  active boolean not null default true,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index delivery_zones_website_id_idx on public.delivery_zones(website_id);
create index delivery_zones_polygon_gix on public.delivery_zones using gist (polygon);

-- Recreate FK from orders.delivery_zone_id
alter table if exists public.orders
  add constraint orders_delivery_zone_id_fkey
  foreign key (delivery_zone_id) references public.delivery_zones(id)
  on delete set null;

-- =====================================================
-- RLS
-- =====================================================
alter table public.delivery_zones enable row level security;

create policy "owners read own zones"
  on public.delivery_zones for select
  using (
    website_id in (
      select id from public.websites where user_id = auth.uid()
    )
  );

create policy "owners write own zones"
  on public.delivery_zones for all
  using (
    website_id in (
      select id from public.websites where user_id = auth.uid()
    )
  )
  with check (
    website_id in (
      select id from public.websites where user_id = auth.uid()
    )
  );

create policy "public can read active zones"
  on public.delivery_zones for select
  to anon
  using (active = true);

grant select on public.delivery_zones to anon;
grant all on public.delivery_zones to authenticated;
grant all on public.delivery_zones to service_role;

-- =====================================================
-- updated_at trigger
-- =====================================================
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

create trigger delivery_zones_updated_at
  before update on public.delivery_zones
  for each row execute function public.set_updated_at();

-- =====================================================
-- find_zone_for_point — used by postcode test + customer flow
-- Returns the smallest active zone covering the given point.
-- =====================================================
create or replace function public.find_zone_for_point(
  p_website_id uuid,
  p_lat double precision,
  p_lng double precision
)
returns table (
  id uuid,
  name text,
  fee_cents integer,
  min_order_cents integer,
  color text
) language sql stable as $$
  select id, name, fee_cents, min_order_cents, color
  from public.delivery_zones
  where website_id = p_website_id
    and active = true
    and ST_Covers(polygon, ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography)
  order by ST_Area(polygon::geography) asc
  limit 1;
$$;

grant execute on function public.find_zone_for_point(uuid, double precision, double precision)
  to anon, authenticated;

-- =====================================================
-- insert_delivery_zone — RPC used by FastAPI to convert
-- GeoJSON polygon into geography column server-side. Runs as
-- security definer but enforces ownership against websites.user_id.
-- =====================================================
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
  p_active boolean
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
    estimated_delivery_min, max_simultaneous_orders, customer_notes, active
  ) values (
    p_website_id, p_name, p_color,
    p_fee_cents, p_min_order_cents,
    ST_GeomFromGeoJSON(p_polygon_geojson)::geography,
    p_schedule_json, p_estimated_delivery_min, p_max_simultaneous_orders,
    p_customer_notes, p_active
  ) returning id into v_id;

  return v_id;
end $$;

grant execute on function public.insert_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean)
  to authenticated;

-- =====================================================
-- update_delivery_zone — partial update RPC (handles polygon
-- conversion when polygon GeoJSON is provided).
-- =====================================================
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
  p_active boolean
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
    active                  = coalesce(p_active, active)
  where id = p_zone_id;

  return p_zone_id;
end $$;

grant execute on function public.update_delivery_zone(uuid, text, text, integer, integer, text, jsonb, integer, integer, text, boolean)
  to authenticated;

-- =====================================================
-- list_delivery_zones — returns zones with polygon as GeoJSON
-- and computed area_m2 so the frontend can render and stat
-- without holding raw PostGIS types.
-- =====================================================
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
  created_at timestamptz,
  updated_at timestamptz
) language sql stable as $$
  select
    z.id,
    z.website_id,
    z.name,
    z.color,
    z.fee_cents,
    z.min_order_cents,
    ST_AsGeoJSON(z.polygon)::jsonb as polygon_geojson,
    z.schedule_json,
    z.estimated_delivery_min,
    z.max_simultaneous_orders,
    z.customer_notes,
    z.active,
    ST_Area(z.polygon::geography) as area_m2,
    z.created_at,
    z.updated_at
  from public.delivery_zones z
  where z.website_id = p_website_id
  order by z.created_at asc;
$$;

grant execute on function public.list_delivery_zones(uuid) to authenticated;

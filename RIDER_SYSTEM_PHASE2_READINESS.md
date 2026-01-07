## Phase 2 readiness (what already exists)

- **Tracking fields exist in DB**: `delivery_orders.rider_id`, `delivery_orders.delivery_latitude/delivery_longitude`, and rider status/location fields in `riders` (`is_online`, `current_latitude/current_longitude`, `last_location_update`).
- **Location history table exists**: `rider_locations` stores per-order GPS samples (`latitude`, `longitude`, `recorded_at`).
- **Realtime hooks are pre-wired in SQL**: `backend/migrations/002_delivery_system.sql` adds `delivery_orders`, `rider_locations`, and `order_status_history` to `supabase_realtime` publication.
- **Schemas already exist**: `backend/app/models/delivery_schemas.py` contains `RiderLocationUpdate` and `RiderStatusUpdate` models that match Phase 2 concepts (GPS + online/offline).

## Phase 1 safety (kept inactive)

- **No public GPS exposure**: the public order tracking endpoint returns **basic rider info only** and forces `current_latitude/current_longitude = null`, and does not return `rider_locations`.
- **Widget tracking UI explicitly avoids GPS/maps**: the customer “tracking” view shows rider basics (name/phone/vehicle) once assigned, and states that GPS is not shown in Phase 1.

## What’s still missing for Phase 2 (not implemented here)

- **Rider authentication / rider app**: there are no endpoints for riders to sign in and get a rider-scoped token, and no rider-facing UI.
- **Location update endpoints**: there is no API route that lets a rider post GPS updates to `rider_locations` and update `riders.current_latitude/current_longitude`.
- **Online/offline endpoints**: there is no API route to update `riders.is_online` for a rider app session.
- **Realtime client wiring**: the frontend does not subscribe to Supabase realtime streams for `delivery_orders` / `rider_locations` yet.

## Phase 2 suggested integration (when you’re ready)

- **Rider app auth**: use Supabase auth (recommended) or a separate rider JWT and map it to a `riders.id`.
- **Location updates**: add rider-authenticated endpoints that:
  - insert into `rider_locations` for the active order (history),
  - update `riders.current_latitude/current_longitude` + `last_location_update` (latest),
  - never expose rider GPS publicly (customer gets GPS only via controlled tracking view if you choose).
- **Realtime**: subscribe to `delivery_orders` for status changes and `rider_locations` for location streams (maps), behind Phase 2 feature flags.


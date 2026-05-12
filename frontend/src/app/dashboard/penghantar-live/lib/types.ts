// Penghantar Live — shared types.
// Backend contract: backend/app/api/v1/endpoints/penghantar_live.py
//
// We keep snake_case field names from the API response (no camelCase conversion)
// to avoid a serialization layer and so the wire format is trivially debuggable.

// ----- Outlet (re-used shape from penghantaran) -----

export interface Outlet {
  id: string;
  name: string;
  subdomain: string;
  lat: number | null;
  lng: number | null;
  location_address?: string | null;
  business_name?: string | null;
}

// ----- Order status (canonical English from DB) -----

export type OrderStatus =
  | 'pending'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'picked_up'
  | 'delivering'
  | 'delivered'
  | 'completed'
  | 'cancelled';

/** Active statuses returned by GET /live/website/{id}/orders. */
export const ACTIVE_STATUSES: ReadonlySet<OrderStatus> = new Set([
  'pending',
  'confirmed',
  'preparing',
  'ready',
  'picked_up',
  'delivering',
]);

/** Malay labels shown in the UI. Centralized so labels stay consistent
 *  across cards, pills, and modals. */
export const STATUS_LABELS_MS: Record<OrderStatus, string> = {
  pending: 'Baru diterima',
  confirmed: 'Disahkan',
  preparing: 'Sedang siap',
  ready: 'Siap diambil',
  picked_up: 'Diambil rider',
  delivering: 'Sedang dihantar',
  delivered: 'Telah dihantar',
  completed: 'Selesai',
  cancelled: 'Dibatalkan',
};

// ----- Order items -----

export interface OrderItem {
  id: string | null;
  menu_item_id: string | null;
  item_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  options: unknown;
  notes: string | null;
}

// ----- Active order (response from GET /live/website/{id}/orders) -----

export interface ActiveOrder {
  id: string;
  order_number: string;
  customer_name: string;
  customer_phone: string;
  delivery_address: string;
  delivery_latitude: number | null;
  delivery_longitude: number | null;
  items: OrderItem[];
  subtotal: number;
  delivery_fee: number;
  total_amount: number;
  status: OrderStatus;
  created_at: string;
  picked_up_at: string | null;
  estimated_delivery_time: number | null;
  eta_at: string | null;

  // Denormalized rider snapshot (null when no rider assigned).
  rider_id: string | null;
  rider_name: string | null;
  rider_phone: string | null;
  rider_vehicle_plate: string | null;
  rider_current_latitude: number | null;
  rider_current_longitude: number | null;
  rider_last_location_update: string | null;
  rider_is_online: boolean | null;

  // Denormalized zone snapshot (null when no zone matched).
  delivery_zone_id: string | null;
  zone_name: string | null;
  zone_color: string | null;
  zone_outer_radius_m: number | null;
}

// ----- Live rider (response from GET /live/website/{id}/riders) -----

export interface LiveRider {
  id: string;
  name: string;
  phone: string;
  vehicle_plate: string | null;
  vehicle_type: string | null;
  vehicle_model: string | null;
  is_active: boolean;
  is_online: boolean;
  current_latitude: number | null;
  current_longitude: number | null;
  last_location_update: string | null;

  // Most-recent active order info, null when rider has none.
  active_order_id: string | null;
  active_order_number: string | null;
  active_order_eta_at: string | null;
  active_order_status: OrderStatus | null;

  today_deliveries: number;
}

// ----- Zone (subset reused for map overlay only) -----
// Full zone model lives in /dashboard/penghantaran. We only need polygon +
// styling fields to draw the overlay; the rest is owned by the zones page.

export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface LiteZone {
  id: string;
  name: string;
  color: string;
  polygon: GeoJSONPolygon;
  active: boolean;
  inner_radius_m: number | null;
  outer_radius_m: number | null;
}

// ----- UI tiers computed from is_online + last_location_update freshness -----

export type RiderPresence = 'online' | 'online_stale_gps' | 'offline';

/** UI presence tiers — 5 minute freshness threshold for GPS. */
export function computeRiderPresence(rider: LiveRider): RiderPresence {
  if (!rider.is_online) return 'offline';
  if (!rider.last_location_update) return 'online_stale_gps';
  const ageMs = Date.now() - new Date(rider.last_location_update).getTime();
  return ageMs > 5 * 60 * 1000 ? 'online_stale_gps' : 'online';
}

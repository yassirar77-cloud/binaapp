// Penghantaran (Delivery Zone Management) — shared types
// Backend contract lives in backend/app/api/v1/endpoints/delivery_zones.py

// ----- GeoJSON -----

/**
 * GeoJSON Polygon. Coordinates are [lng, lat] per RFC 7946.
 * The first ring is the outer boundary; we don't use holes.
 * coordinates: [[[lng, lat], [lng, lat], ..., [lng, lat]]]  // closed (first === last)
 */
export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

// ----- Schedule -----

export interface ScheduleDay {
  open: string;   // "HH:MM"
  close: string;  // "HH:MM"
  active: boolean;
}

export type DayKey = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun';

export type ScheduleJson = Record<DayKey, ScheduleDay>;

// ----- Outlet (alias for Website in BinaApp's data model) -----
// Each website is one outlet (1:1 for v1). Renamed in UI as "kedai".

export interface Outlet {
  id: string;            // websites.id
  name: string;          // websites.business_name || websites.name
  subdomain: string;
  lat: number | null;    // websites.lat
  lng: number | null;    // websites.lng
  location_address?: string | null;
  business_name?: string | null;
}

// ----- Zone -----

export interface Zone {
  id: string;
  website_id: string;
  name: string;
  color: string;
  fee_cents: number;
  min_order_cents: number;
  polygon: GeoJSONPolygon;
  schedule_json: ScheduleJson;
  estimated_delivery_min: number | null;
  max_simultaneous_orders: number | null;
  customer_notes: string | null;
  active: boolean;
  area_m2: number | null;
  inner_radius_m: number | null;
  outer_radius_m: number | null;
  created_at: string;
  updated_at: string;
}

/** Payload for POST /zones/website/{website_id} */
export interface ZoneInput {
  name: string;
  color: string;
  fee_cents: number;
  min_order_cents: number;
  polygon: GeoJSONPolygon;
  schedule_json?: ScheduleJson;
  estimated_delivery_min?: number;
  max_simultaneous_orders?: number;
  customer_notes?: string | null;
  active?: boolean;
  inner_radius_m?: number | null;
  outer_radius_m?: number | null;
}

// ----- Postcode test -----

export interface PostcodeTestResult {
  covered: boolean;
  zone_id: string | null;
  name: string | null;
  fee_cents: number | null;
  min_order_cents: number | null;
  color: string | null;
}

// ----- Riders -----
// Backend contract: /api/v1/delivery/admin/websites/{websiteId}/riders
//                   /api/v1/delivery/riders/{riderId}

export type VehicleType = 'motorcycle' | 'car' | 'bicycle' | 'scooter';

export interface Rider {
  id: string;
  website_id: string;
  name: string;
  phone: string;
  email: string | null;
  photo_url: string | null;
  vehicle_type: string | null;
  vehicle_plate: string | null;
  vehicle_model: string | null;
  is_active: boolean;
  is_online: boolean;
  total_deliveries: number;
  /** May come back as a decimal string from the API. */
  rating: number | string | null;
  total_ratings: number;
  last_location_update: string | null;
  created_at: string;
}

/** Payload for POST .../riders */
export interface RiderCreateInput {
  name: string;
  phone: string;
  email?: string;
  vehicle_type?: string;
  vehicle_plate?: string;
  vehicle_model?: string;
  is_active: boolean;
  /** Min 6 characters. */
  password: string;
}

/** Payload for PUT /riders/{riderId} — any subset; password (min 6) resets login. */
export interface RiderUpdateInput {
  name?: string;
  phone?: string;
  email?: string;
  vehicle_type?: string;
  vehicle_plate?: string;
  vehicle_model?: string;
  is_active?: boolean;
  password?: string;
}

/** Structured 403 detail returned when the plan's rider limit is reached. */
export interface RiderLimitDetail {
  error: 'limit_reached';
  message?: string;
  can_buy_addon?: boolean;
  addon_price?: number;
  [key: string]: unknown;
}

// ----- Delivery settings -----
// Backend contract: /api/v1/delivery/admin/websites/{websiteId}/settings

/**
 * Numeric fields may come back as strings (decimals) from the API —
 * normalise with Number() before displaying.
 */
export interface DeliverySettings {
  delivery_enabled: boolean;
  default_delivery_fee: number | string;
  minimum_order: number | string;
  max_delivery_distance: number | string;
  pickup_enabled: boolean;
  pickup_address: string | null;
  accept_cod: boolean;
  accept_online: boolean;
  accept_ewallet: boolean;
  notify_whatsapp: boolean;
  whatsapp_number: string | null;
  notify_email: boolean;
  notify_sound: boolean;
}

/** Partial update — send only modified keys (exclude_unset semantics). */
export interface DeliverySettingsUpdate {
  delivery_enabled?: boolean;
  default_delivery_fee?: number;
  minimum_order?: number;
  max_delivery_distance?: number;
  pickup_enabled?: boolean;
  pickup_address?: string;
  accept_cod?: boolean;
  accept_online?: boolean;
  accept_ewallet?: boolean;
  notify_whatsapp?: boolean;
  whatsapp_number?: string;
  notify_email?: boolean;
  notify_sound?: boolean;
}

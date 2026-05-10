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
  lat: number | null;    // websites.lat (column not yet added; falls back to KL)
  lng: number | null;    // websites.lng (column not yet added)
  location_address?: string | null;
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

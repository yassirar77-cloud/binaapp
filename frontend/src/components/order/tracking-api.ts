/**
 * API client for the customer-facing tracking page.
 *
 * Wraps `GET /api/v1/delivery/orders/{order_number}/track` — the
 * existing public tracking endpoint that returns order + items +
 * status_history + rider + rider_location.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

/* ----- Backend response shapes ------------------------------------------ */

interface BackendOrder {
  id: string
  order_number: string
  status: string
  created_at?: string | null
  confirmed_at?: string | null
  customer_name?: string | null
  customer_phone?: string | null
  customer_email?: string | null
  delivery_address?: string | null
  total_amount?: number | string | null
  delivery_fee?: number | string | null
  subtotal?: number | string | null
  payment_method?: string | null
  rider_id?: string | null
  website_id?: string | null
  delivery_latitude?: number | null
  delivery_longitude?: number | null
  estimated_delivery_time?: number | null
}

interface BackendOrderItem {
  id: string
  order_id: string
  menu_item_id?: string | null
  item_name: string
  quantity: number
  unit_price: number | string
  total_price: number | string
  options?: unknown
  notes?: string | null
}

interface BackendStatusHistoryEntry {
  id: string
  order_id: string
  status: string
  notes?: string | null
  updated_by?: string | null
  created_at: string
}

interface BackendRider {
  id: string
  name?: string | null
  phone?: string | null
  photo_url?: string | null
  vehicle_type?: string | null
  vehicle_plate?: string | null
  rating?: number | null
  current_latitude?: number | null
  current_longitude?: number | null
  last_location_update?: string | null
}

interface BackendRiderLocation {
  latitude: number
  longitude: number
  recorded_at: string
}

interface BackendTrackResponse {
  order: BackendOrder
  items: BackendOrderItem[]
  status_history: BackendStatusHistoryEntry[]
  rider: BackendRider | null
  rider_location: BackendRiderLocation | null
  eta_minutes: number | null
}

/* ----- Normalized shapes consumed by the UI ----------------------------- */

export interface TrackedOrder {
  id: string
  orderNumber: string
  status: string
  createdAt: string | null
  confirmedAt: string | null
  customerName: string
  customerPhone: string
  deliveryAddress: string
  subtotal: number
  deliveryFee: number
  totalAmount: number
  paymentMethod: string
  websiteId: string | null
  deliveryLatitude: number | null
  deliveryLongitude: number | null
  estimatedDeliveryTime: number | null
}

export interface TrackedOrderItem {
  id: string
  name: string
  quantity: number
  unitPrice: number
  totalPrice: number
  notes: string
}

export interface TrackedRider {
  id: string
  name: string
  phone: string
  photoUrl: string | null
  vehicleType: string
  vehiclePlate: string
  rating: number | null
}

export interface TrackedLocation {
  latitude: number
  longitude: number
  recordedAt: string
}

export interface TrackedOrderDetail {
  order: TrackedOrder
  items: TrackedOrderItem[]
  rider: TrackedRider | null
  riderLocation: TrackedLocation | null
  etaMinutes: number | null
}

/* ----- Normalizers ------------------------------------------------------ */

const num = (v: number | string | null | undefined): number =>
  typeof v === 'number' ? v : v != null ? Number(v) || 0 : 0

const numOrNull = (v: number | string | null | undefined): number | null => {
  if (v == null) return null
  const n = typeof v === 'number' ? v : Number(v)
  return Number.isFinite(n) ? n : null
}

function normalizeOrder(raw: BackendOrder): TrackedOrder {
  return {
    id: raw.id,
    orderNumber: raw.order_number,
    status: raw.status,
    createdAt: raw.created_at ?? null,
    confirmedAt: raw.confirmed_at ?? null,
    customerName: raw.customer_name ?? '',
    customerPhone: raw.customer_phone ?? '',
    deliveryAddress: raw.delivery_address ?? '',
    subtotal: num(raw.subtotal),
    deliveryFee: num(raw.delivery_fee),
    totalAmount: num(raw.total_amount),
    paymentMethod: raw.payment_method ?? '',
    websiteId: raw.website_id ?? null,
    deliveryLatitude: numOrNull(raw.delivery_latitude),
    deliveryLongitude: numOrNull(raw.delivery_longitude),
    estimatedDeliveryTime: raw.estimated_delivery_time ?? null,
  }
}

function normalizeItems(raws: BackendOrderItem[]): TrackedOrderItem[] {
  return (raws || []).map((r) => ({
    id: r.id,
    name: r.item_name,
    quantity: r.quantity,
    unitPrice: num(r.unit_price),
    totalPrice: num(r.total_price),
    notes: r.notes ?? '',
  }))
}

function normalizeRider(raw: BackendRider | null): TrackedRider | null {
  if (!raw) return null
  return {
    id: raw.id,
    name: raw.name ?? 'Rider',
    phone: raw.phone ?? '',
    photoUrl: raw.photo_url ?? null,
    vehicleType: raw.vehicle_type ?? '',
    vehiclePlate: raw.vehicle_plate ?? '',
    rating: raw.rating ?? null,
  }
}

function normalizeLocation(raw: BackendRiderLocation | null): TrackedLocation | null {
  if (!raw) return null
  return {
    latitude: Number(raw.latitude),
    longitude: Number(raw.longitude),
    recordedAt: raw.recorded_at,
  }
}

/* ----- Fetcher ---------------------------------------------------------- */

export class TrackOrderError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message)
    this.name = 'TrackOrderError'
  }
}

/**
 * Fetch + normalize the tracking payload.
 *
 * Throws `TrackOrderError(404)` when the order_number is unknown — the
 * page surfaces a dedicated "Pesanan tidak ditemui" state for that.
 */
export async function fetchTrackedOrder(
  orderNumber: string,
  signal?: AbortSignal
): Promise<TrackedOrderDetail> {
  const url =
    `${API_BASE}/api/v1/delivery/orders/${encodeURIComponent(orderNumber)}/track`

  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
    signal,
  })

  if (!res.ok) {
    throw new TrackOrderError(
      res.status === 404 ? 'Pesanan tidak ditemui.' : `Gagal memuatkan pesanan (${res.status})`,
      res.status
    )
  }

  const raw = (await res.json()) as BackendTrackResponse

  return {
    order: normalizeOrder(raw.order),
    items: normalizeItems(raw.items),
    rider: normalizeRider(raw.rider),
    riderLocation: normalizeLocation(raw.rider_location),
    etaMinutes: raw.eta_minutes ?? null,
  }
}

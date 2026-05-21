/**
 * API client for the checkout flow.
 *
 * Three endpoints today, all public (no auth):
 *   - GET  /api/v1/delivery/geocode-address?q=          typed-address → lat/lng
 *   - GET  /api/v1/delivery/zones/{website_id}/cover    lat/lng → covering ring
 *   - POST /api/v1/delivery/orders                      place an order
 *
 * The customer never picks a ring — coverage is auto-detected from the
 * delivery coordinates server-side. The dropdown that used to live here
 * is gone (PR: connect-delivery-zones); see CoverageStatusSection in the
 * adjacent checkout/ folder for the new UI.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

const num = (v: string | number | null | undefined): number =>
  typeof v === 'number' ? v : Number(v ?? 0) || 0

/* ----- Ring coverage ---------------------------------------------------- */

/** Ring info as returned by /zones/{id}/cover. Fees are in RM. */
export interface CoveredZone {
  id: string
  name: string
  fee: number
  /** Minimum subtotal (RM) required to checkout in this ring. 0 = no minimum. */
  minOrder: number
  color: string
}

export type CoverResponse =
  | { covered: true; zone: CoveredZone }
  | { covered: false }

interface BackendCoveredZone {
  id: string
  name: string
  fee: string | number
  min_order: string | number
  color: string
}

interface BackendCoverResponse {
  covered: boolean
  zone: BackendCoveredZone | null
}

export class CoverageError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message)
    this.name = 'CoverageError'
  }
}

export async function fetchZoneCoverage(
  websiteId: string,
  lat: number,
  lng: number,
  signal?: AbortSignal
): Promise<CoverResponse> {
  const url =
    `${API_BASE}/api/v1/delivery/zones/${encodeURIComponent(websiteId)}/cover` +
    `?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
    signal,
  })
  if (!res.ok) {
    throw new CoverageError(`Coverage lookup failed (${res.status})`, res.status)
  }
  const raw = (await res.json()) as BackendCoverResponse
  if (!raw.covered || !raw.zone) {
    return { covered: false }
  }
  return {
    covered: true,
    zone: {
      id: raw.zone.id,
      name: raw.zone.name,
      fee: num(raw.zone.fee),
      minOrder: num(raw.zone.min_order),
      color: raw.zone.color,
    },
  }
}

/* ----- Address geocode -------------------------------------------------- */

export interface GeocodeHit {
  found: boolean
  lat?: number
  lng?: number
  displayName?: string
}

interface BackendGeocodeResult {
  found: boolean
  lat: number | null
  lng: number | null
  display_name: string | null
}

export class GeocodeError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message)
    this.name = 'GeocodeError'
  }
}

export async function geocodeAddress(
  q: string,
  signal?: AbortSignal
): Promise<GeocodeHit> {
  const url =
    `${API_BASE}/api/v1/delivery/geocode-address?q=${encodeURIComponent(q)}`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
    signal,
  })
  if (!res.ok) {
    throw new GeocodeError(`Geocode failed (${res.status})`, res.status)
  }
  const raw = (await res.json()) as BackendGeocodeResult
  if (!raw.found || raw.lat == null || raw.lng == null) {
    return { found: false }
  }
  return {
    found: true,
    lat: raw.lat,
    lng: raw.lng,
    displayName: raw.display_name ?? undefined,
  }
}

/* ----- Order placement -------------------------------------------------- */

/**
 * BinaApp does not process customer food-order payments. The customer
 * checkout flow only ever submits `cod`; the backend's broader
 * PaymentMethod enum is irrelevant on the customer side.
 */
export type OrderPaymentMethod = 'cod'

export interface OrderItemPayload {
  menu_item_id: string
  quantity: number
  notes?: string
}

export interface PlaceOrderPayload {
  website_id: string
  customer_name: string
  customer_phone: string
  customer_email?: string
  delivery_address: string
  /** Required: server resolves the ring + fee from these. */
  delivery_latitude: number
  /** Required: server resolves the ring + fee from these. */
  delivery_longitude: number
  delivery_notes?: string
  /**
   * The server ignores this field and recomputes the ring from
   * delivery_latitude/longitude (closes the fee-spoofing hole). We still
   * send the auto-detected id so the server's mismatch-telemetry warning
   * doesn't fire for our own checkout.
   */
  delivery_zone_id?: string
  items: OrderItemPayload[]
  payment_method: OrderPaymentMethod
}

/** Slice of the OrderResponse the UI actually consumes. */
export interface PlacedOrder {
  id: string
  order_number: string
  status: string
  payment_method: string
  payment_status: string
  delivery_fee: number
  subtotal: number
  total_amount: number
  created_at: string
  /** Conversation ID from the order-creation flow — useful for chat in PR 6+. */
  conversation_id?: string | null
}

export class PlaceOrderError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message)
    this.name = 'PlaceOrderError'
  }
}

export async function placeOrder(payload: PlaceOrderPayload): Promise<PlacedOrder> {
  const url = `${API_BASE}/api/v1/delivery/orders`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let detail = ''
    let code: string | undefined
    try {
      const body = await res.json()
      const detailObj = body?.detail
      if (typeof detailObj === 'string') {
        detail = detailObj
      } else if (detailObj && typeof detailObj === 'object') {
        detail = detailObj.message || ''
        code = detailObj.error
      }
    } catch {
      // ignore — body wasn't JSON
    }
    throw new PlaceOrderError(
      detail || `Gagal membuat pesanan (${res.status})`,
      res.status,
      code
    )
  }

  const raw = await res.json()
  return {
    id: raw.id,
    order_number: raw.order_number,
    status: raw.status,
    payment_method: raw.payment_method,
    payment_status: raw.payment_status,
    delivery_fee: num(raw.delivery_fee),
    subtotal: num(raw.subtotal),
    total_amount: num(raw.total_amount),
    created_at: raw.created_at,
    conversation_id: raw.conversation_id ?? null,
  }
}

/**
 * API client for the checkout flow.
 *
 * Two endpoints today:
 *   - GET  /api/v1/delivery/zones/{website_id}    fetch zones + settings
 *   - POST /api/v1/delivery/orders                place an order
 *
 * Both are public (no auth) — same model as the menu and customer-lookup
 * endpoints used by earlier PRs.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

/* ----- Delivery zones --------------------------------------------------- */

interface BackendZone {
  id: string
  website_id: string
  zone_name: string
  zone_polygon?: unknown
  center_lat?: string | number | null
  center_lng?: string | number | null
  radius_km?: string | number | null
  delivery_fee: string | number
  minimum_order: string | number
  estimated_time_min: number
  estimated_time_max: number
  is_active: boolean
  sort_order: number
}

interface BackendZonesResponse {
  zones: BackendZone[]
  settings?: unknown
}

/** Normalized zone shape consumed by the UI. */
export interface DeliveryZone {
  id: string
  name: string
  fee: number
  /** Minimum subtotal (RM) required to checkout in this zone. 0 = no minimum. */
  minOrder: number
  etaMin: number
  etaMax: number
}

const num = (v: string | number | null | undefined): number =>
  typeof v === 'number' ? v : Number(v ?? 0) || 0

function normalizeZone(raw: BackendZone): DeliveryZone {
  return {
    id: raw.id,
    name: raw.zone_name,
    fee: num(raw.delivery_fee),
    minOrder: num(raw.minimum_order),
    etaMin: raw.estimated_time_min ?? 0,
    etaMax: raw.estimated_time_max ?? 0,
  }
}

export class ZoneFetchError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message)
    this.name = 'ZoneFetchError'
  }
}

export async function fetchDeliveryZones(websiteId: string): Promise<DeliveryZone[]> {
  const url = `${API_BASE}/api/v1/delivery/zones/${encodeURIComponent(websiteId)}`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new ZoneFetchError(`Zone fetch failed (${res.status})`, res.status)
  }
  const raw = (await res.json()) as BackendZonesResponse
  return (raw.zones || []).map(normalizeZone)
}

/* ----- Order placement -------------------------------------------------- */

/** Maps to the backend `PaymentMethod` enum (cod | online | ewallet). */
export type OrderPaymentMethod = 'cod' | 'online' | 'ewallet'

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
  delivery_latitude?: number
  delivery_longitude?: number
  delivery_notes?: string
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
  /**
   * Future field. Today the backend does NOT return a payment_url for
   * `online` payment_method — ToyyibPay create_bill is not wired into
   * POST /orders yet. See TODO(payment) in PaymentMethodSection.
   */
  payment_url?: string | null
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
    payment_url: raw.payment_url ?? null,
  }
}

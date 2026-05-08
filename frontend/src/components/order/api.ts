/**
 * API client for the customer-facing /order flow.
 *
 * Separate from the owner-side `lib/api.ts` because customer-flow
 * endpoints are public — there's no JWT, no token refresh, and no
 * 401-redirect-to-login machinery. Customers identify by phone only.
 */

import type { CustomerLookupResponse } from './types'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

/** Thrown when the lookup endpoint returns a non-OK status. */
export class CustomerLookupError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message)
    this.name = 'CustomerLookupError'
  }
}

/**
 * Look up a saved customer for the given website + phone.
 *
 * Returns `{ exists: false }` for unknown phones (200 OK, treated as
 * "new customer" in the UI). Throws `CustomerLookupError` on any
 * non-OK status — callers should fall back to "treat as new customer"
 * so a flaky backend never blocks a customer from ordering.
 */
export async function lookupCustomer(
  websiteId: string,
  phone: string,
  signal?: AbortSignal
): Promise<CustomerLookupResponse> {
  const url = new URL(`${API_BASE}/api/v1/customers/lookup`)
  url.searchParams.set('website_id', websiteId)
  url.searchParams.set('phone', phone)

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = typeof body?.detail === 'string' ? body.detail : body?.detail?.message || ''
    } catch {
      // ignore — body wasn't JSON
    }
    throw new CustomerLookupError(
      detail || `Customer lookup failed (${res.status})`,
      res.status
    )
  }

  return (await res.json()) as CustomerLookupResponse
}

/** A single active order returned by the active-orders endpoint. */
export interface ActiveOrder {
  order_number: string
  restaurant_name: string
  restaurant_subdomain: string
  status: string
  total: number
  created_at: string
}

/**
 * Fetch a customer's active (non-terminal) orders for a given restaurant.
 *
 * Returns an empty array when nothing is active — callers should hide the
 * section rather than showing an empty state.
 */
export async function fetchActiveOrders(
  websiteId: string,
  phone: string,
  signal?: AbortSignal
): Promise<ActiveOrder[]> {
  const url = new URL(
    `${API_BASE}/api/v1/customers/${encodeURIComponent(phone)}/active-orders`
  )
  url.searchParams.set('website_id', websiteId)

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!res.ok) return []

  const body = await res.json()
  return (body.orders ?? []) as ActiveOrder[]
}

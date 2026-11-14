'use client'

import { useEffect, useState } from 'react'
import { cartTotal, useCartStore } from './cart-store'
import { useCustomerStore } from './customer-store'
import { useRestaurant } from './ThemeProvider'

/**
 * Voucher codes and loyalty points for the customer order flow.
 *
 * Every amount here comes from `POST /api/v1/promotions/quote` — the
 * client never computes a discount itself. The quote is only a preview:
 * the order endpoint re-validates the code and recomputes the totals, and
 * refuses the order (rather than silently charging full price) if a
 * promotion the customer was shown can no longer be honoured.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

export interface VoucherQuote {
  code: string
  valid: boolean
  discount: number
  /** e.g. "10% diskaun (maks RM5.00)". Empty when the code is not valid. */
  summary: string
  message: string
}

export interface LoyaltyQuote {
  enabled: boolean
  balance: number
  /** Points that would be spent if the customer redeems now. */
  redeemablePoints: number
  redeemDiscount: number
  /** Points this order will earn once it is completed. */
  willEarn: number
  /** Every `redeemPoints` points are worth RM `redeemValue`. */
  redeemPoints: number
  redeemValue: number
  applied: boolean
}

export interface PromoQuote {
  subtotal: number
  voucher: VoucherQuote | null
  loyalty: LoyaltyQuote
  discountTotal: number
  payableSubtotal: number
}

export interface PromoQuoteRequest {
  websiteId: string
  subtotal: number
  phone?: string
  voucherCode?: string | null
  redeemPoints?: boolean
}

export class PromoQuoteError extends Error {
  constructor(message: string, public status: number) {
    super(message)
    this.name = 'PromoQuoteError'
  }
}

const n = (v: unknown): number => {
  const parsed = typeof v === 'number' ? v : parseFloat(String(v ?? 0))
  return Number.isFinite(parsed) ? parsed : 0
}

/** What customers type → what the server stores ("jimat-10" → "JIMAT10"). */
export function normalizePromoCode(raw: string | null | undefined): string {
  return (raw || '').replace(/[\s-]/g, '').toUpperCase()
}

export const NO_LOYALTY: LoyaltyQuote = {
  enabled: false,
  balance: 0,
  redeemablePoints: 0,
  redeemDiscount: 0,
  willEarn: 0,
  redeemPoints: 100,
  redeemValue: 5,
  applied: false,
}

export function parsePromoQuote(raw: any): PromoQuote {
  const v = raw?.voucher
  const l = raw?.loyalty
  return {
    subtotal: n(raw?.subtotal),
    voucher: v
      ? {
          code: String(v.code || ''),
          valid: !!v.valid,
          discount: v.valid ? n(v.discount) : 0,
          summary: String(v.summary || ''),
          message: String(v.message || ''),
        }
      : null,
    loyalty: l
      ? {
          enabled: !!l.enabled,
          balance: n(l.balance),
          redeemablePoints: n(l.redeemable_points),
          redeemDiscount: n(l.redeem_discount),
          willEarn: n(l.will_earn),
          redeemPoints: n(l.redeem_points) || 100,
          redeemValue: n(l.redeem_value) || 5,
          applied: !!l.applied,
        }
      : NO_LOYALTY,
    discountTotal: n(raw?.discount_total),
    payableSubtotal: n(raw?.payable_subtotal),
  }
}

export async function fetchPromoQuote(
  req: PromoQuoteRequest,
  signal?: AbortSignal
): Promise<PromoQuote> {
  const res = await fetch(`${API_BASE}/api/v1/promotions/quote`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({
      website_id: req.websiteId,
      subtotal: Number(req.subtotal.toFixed(2)),
      customer_phone: req.phone || undefined,
      voucher_code: req.voucherCode || undefined,
      redeem_points: !!req.redeemPoints,
    }),
    signal,
  })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = typeof body?.detail === 'string' ? body.detail : ''
    } catch {
      /* not JSON */
    }
    throw new PromoQuoteError(detail || `Gagal menyemak promosi (${res.status})`, res.status)
  }
  return parsePromoQuote(await res.json())
}

/* ----- Shared, de-duplicated quote -------------------------------------- */

// The cart summary, the checkout button and the checkout page all need the
// same quote at the same moment. One in-flight request per distinct input
// serves them all, which also keeps a customer tapping the quantity stepper
// well inside the endpoint's rate limit.
const inflight = new Map<string, Promise<PromoQuote>>()
const settled = new Map<string, PromoQuote>()
const SETTLED_MAX = 20

function requestKey(req: PromoQuoteRequest): string {
  return [
    req.websiteId,
    req.subtotal.toFixed(2),
    req.phone || '',
    normalizePromoCode(req.voucherCode),
    req.redeemPoints ? '1' : '0',
  ].join('|')
}

function sharedQuote(req: PromoQuoteRequest): Promise<PromoQuote> {
  const key = requestKey(req)
  const cached = settled.get(key)
  if (cached) return Promise.resolve(cached)
  let pending = inflight.get(key)
  if (!pending) {
    pending = fetchPromoQuote(req)
      .then((quote) => {
        settled.set(key, quote)
        if (settled.size > SETTLED_MAX) {
          settled.delete(settled.keys().next().value as string)
        }
        return quote
      })
      .finally(() => inflight.delete(key))
    inflight.set(key, pending)
  }
  return pending
}

/** Forget cached quotes (after an order spends points or a voucher use). */
export function clearPromoQuoteCache(): void {
  settled.clear()
}

export interface PromoQuoteState {
  quote: PromoQuote | null
  /** True while the amounts on screen may be stale. */
  loading: boolean
  error: string | null
}

const DEBOUNCE_MS = 300

/**
 * The live quote for the current cart.
 *
 * `withLoyalty` is false on the cart sheet (only a typed voucher code needs
 * the server there) and true at checkout, where the customer can see their
 * balance and choose to spend it.
 */
export function usePromoQuote(opts: { withLoyalty?: boolean } = {}): PromoQuoteState {
  const withLoyalty = !!opts.withLoyalty
  const restaurant = useRestaurant()
  const subtotal = useCartStore((s) => cartTotal(s.items))
  const promoCode = useCartStore((s) => s.promoCode)
  const redeemPoints = useCartStore((s) => s.redeemPoints)
  const phone = useCustomerStore((s) => s.customer?.phone ?? '')

  const needed = subtotal > 0 && (!!promoCode || withLoyalty)
  const [state, setState] = useState<PromoQuoteState>({
    quote: null,
    loading: needed,
    error: null,
  })

  useEffect(() => {
    if (!needed) {
      setState({ quote: null, loading: false, error: null })
      return
    }
    let active = true
    setState((prev) => ({ ...prev, loading: true, error: null }))
    const timer = setTimeout(() => {
      sharedQuote({
        websiteId: restaurant.websiteId,
        subtotal,
        phone,
        voucherCode: promoCode,
        redeemPoints: withLoyalty && redeemPoints,
      })
        .then((quote) => {
          if (active) setState({ quote, loading: false, error: null })
        })
        .catch((err: unknown) => {
          if (!active) return
          setState({
            quote: null,
            loading: false,
            error:
              err instanceof PromoQuoteError
                ? err.message
                : 'Tidak dapat menyemak promosi. Sila cuba lagi.',
          })
        })
    }, DEBOUNCE_MS)
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [needed, restaurant.websiteId, subtotal, phone, promoCode, redeemPoints, withLoyalty])

  return state
}

/** Voucher discount to show on the cart sheet (0 until a valid quote lands). */
export function voucherDiscountOf(quote: PromoQuote | null): number {
  return quote?.voucher?.valid ? quote.voucher.discount : 0
}

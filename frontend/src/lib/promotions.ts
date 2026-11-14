/**
 * Promotions client — voucher codes and loyalty points (merchant side).
 *
 * Backend: `api/v1/endpoints/promotions.py`. The customer side of the same
 * feature (quotes in the cart and checkout) lives in
 * `components/order/promo.ts`.
 */

import { ensureValidToken, supabase } from '@/lib/supabase'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

export type DiscountType = 'percent' | 'fixed'

export interface Voucher {
  id: string
  website_id: string
  code: string
  description: string
  discount_type: DiscountType
  discount_value: number
  max_discount: number | null
  min_order: number
  starts_at: string | null
  expires_at: string | null
  usage_limit: number | null
  per_customer_limit: number | null
  used_count: number
  is_active: boolean
  /** Server-written one-liner, e.g. "10% diskaun (maks RM5.00)". */
  summary: string
}

/** What the create form collects. Empty strings mean "not set". */
export interface VoucherForm {
  code: string
  description: string
  discount_type: DiscountType
  discount_value: string
  max_discount: string
  min_order: string
  expires_on: string // yyyy-mm-dd, local date; '' = never
  usage_limit: string
  once_per_customer: boolean
}

export const EMPTY_VOUCHER_FORM: VoucherForm = {
  code: '',
  description: '',
  discount_type: 'percent',
  discount_value: '',
  max_discount: '',
  min_order: '',
  expires_on: '',
  usage_limit: '',
  once_per_customer: false,
}

export interface LoyaltySettings {
  enabled: boolean
  points_per_rm: number
  redeem_points: number
  redeem_value: number
}

export interface LoyaltyMember {
  customer_phone: string
  balance: number
  lifetime_earned: number | null
  last_activity_at: string | null
}

/* ----- Pure helpers (unit-tested) --------------------------------------- */

/** "jimat-10 " → "JIMAT10" — the same normalisation the server applies. */
export function normalizeVoucherCode(raw: string): string {
  return (raw || '').replace(/[\s-]/g, '').toUpperCase()
}

const num = (raw: string): number | null => {
  const text = (raw || '').trim().replace(',', '.')
  if (!text) return null
  const value = Number(text)
  return Number.isFinite(value) ? value : NaN
}

/** First problem with the form in Malay, or null when it can be submitted. */
export function voucherFormProblem(form: VoucherForm): string | null {
  const code = normalizeVoucherCode(form.code)
  if (!/^[A-Z0-9]{3,20}$/.test(code)) {
    return 'Kod mesti 3–20 huruf atau nombor, tanpa simbol.'
  }
  const value = num(form.discount_value)
  if (value === null || Number.isNaN(value) || value <= 0) {
    return 'Masukkan nilai diskaun.'
  }
  if (form.discount_type === 'percent' && value > 100) {
    return 'Diskaun peratus mesti antara 1 hingga 100.'
  }
  for (const [raw, label] of [
    [form.max_discount, 'Had maksimum diskaun'],
    [form.min_order, 'Pesanan minimum'],
    [form.usage_limit, 'Had penggunaan'],
  ] as const) {
    const parsed = num(raw)
    if (parsed !== null && (Number.isNaN(parsed) || parsed < 0)) {
      return `${label} tidak sah.`
    }
  }
  const limit = num(form.usage_limit)
  if (limit !== null && (!Number.isInteger(limit) || limit < 1)) {
    return 'Had penggunaan mesti nombor bulat, sekurang-kurangnya 1.'
  }
  if (form.expires_on && !/^\d{4}-\d{2}-\d{2}$/.test(form.expires_on)) {
    return 'Tarikh tamat tidak sah.'
  }
  return null
}

/**
 * The last moment of a local calendar day, as an ISO instant. A voucher
 * that "expires on 30 Nov" must still work at 11pm on 30 Nov in Malaysia,
 * so the day is anchored to Malaysian time (UTC+8, no DST), not to the
 * merchant's browser or to UTC.
 */
export function endOfDayMalaysia(isoDate: string): string {
  return new Date(`${isoDate}T23:59:59+08:00`).toISOString()
}

/** The request body for POST …/vouchers. Call voucherFormProblem first. */
export function voucherPayload(form: VoucherForm): Record<string, unknown> {
  const maxDiscount = num(form.max_discount)
  const minOrder = num(form.min_order)
  const usageLimit = num(form.usage_limit)
  return {
    code: normalizeVoucherCode(form.code),
    description: form.description.trim(),
    discount_type: form.discount_type,
    discount_value: num(form.discount_value),
    // A cap only applies to a percentage; 0 means "no cap".
    max_discount: form.discount_type === 'percent' && maxDiscount ? maxDiscount : null,
    min_order: minOrder || 0,
    expires_at: form.expires_on ? endOfDayMalaysia(form.expires_on) : null,
    usage_limit: usageLimit || null,
    per_customer_limit: form.once_per_customer ? 1 : null,
  }
}

export type VoucherState = 'active' | 'paused' | 'scheduled' | 'expired' | 'used_up'

/** Why a voucher is or is not redeemable right now (mirrors the server). */
export function voucherState(v: Voucher, now: Date = new Date()): VoucherState {
  if (!v.is_active) return 'paused'
  if (v.expires_at && now.getTime() >= new Date(v.expires_at).getTime()) return 'expired'
  if (v.usage_limit != null && v.used_count >= v.usage_limit) return 'used_up'
  if (v.starts_at && now.getTime() < new Date(v.starts_at).getTime()) return 'scheduled'
  return 'active'
}

export const VOUCHER_STATE_LABEL: Record<VoucherState, string> = {
  active: 'Aktif',
  paused: 'Dijeda',
  scheduled: 'Belum bermula',
  expired: 'Tamat tempoh',
  used_up: 'Habis ditebus',
}

/** "3 / 50 ditebus" or "3 ditebus" when there is no limit. */
export function usageText(v: Voucher): string {
  return v.usage_limit != null
    ? `${v.used_count} / ${v.usage_limit} ditebus`
    : `${v.used_count} ditebus`
}

/** A sentence a merchant can read back to check their loyalty settings. */
export function loyaltySummary(s: LoyaltySettings): string {
  const spend = s.points_per_rm > 0 ? s.redeem_points / s.points_per_rm : 0
  return (
    `Pelanggan dapat ${fmt(s.points_per_rm)} mata bagi setiap RM1. ` +
    `${s.redeem_points} mata = RM${s.redeem_value.toFixed(2)} diskaun ` +
    `(selepas belanja kira-kira RM${spend.toFixed(0)}).`
  )
}

const fmt = (value: number): string =>
  Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')

/* ----- API --------------------------------------------------------------- */

export class PromotionsApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
    this.name = 'PromotionsApiError'
  }
}

/** FastAPI errors come as a string, an object, or a list of field errors. */
export function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as any)?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0]
    const msg = typeof first?.msg === 'string' ? first.msg.replace(/^Value error,\s*/, '') : ''
    if (msg) return msg
  }
  if (detail && typeof detail === 'object' && typeof (detail as any).message === 'string') {
    return (detail as any).message
  }
  return fallback
}

async function getToken(): Promise<string> {
  const valid = await ensureValidToken()
  if (valid) return valid
  if (supabase) {
    const { data } = await supabase.auth.getSession()
    if (data.session?.access_token) return data.session.access_token
  }
  throw new PromotionsApiError('Sila log masuk semula.', 401)
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getToken()
  let res: Response
  try {
    res = await fetch(`${API_BASE}/api/v1/promotions${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(init.headers || {}),
      },
    })
  } catch {
    throw new PromotionsApiError('Tiada sambungan. Sila cuba lagi.', 0)
  }
  if (res.status === 204) return null as unknown as T
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    throw new PromotionsApiError(
      errorMessage(body, `Ralat berlaku (${res.status}). Sila cuba lagi.`),
      res.status
    )
  }
  return body as T
}

const toNumber = (v: unknown): number => Number(v) || 0
const toNumberOrNull = (v: unknown): number | null => (v == null ? null : Number(v))

function parseVoucher(raw: any): Voucher {
  return {
    id: raw.id,
    website_id: raw.website_id,
    code: raw.code,
    description: raw.description || '',
    discount_type: raw.discount_type === 'fixed' ? 'fixed' : 'percent',
    discount_value: toNumber(raw.discount_value),
    max_discount: toNumberOrNull(raw.max_discount),
    min_order: toNumber(raw.min_order),
    starts_at: raw.starts_at ?? null,
    expires_at: raw.expires_at ?? null,
    usage_limit: toNumberOrNull(raw.usage_limit),
    per_customer_limit: toNumberOrNull(raw.per_customer_limit),
    used_count: toNumber(raw.used_count),
    is_active: raw.is_active !== false,
    summary: raw.summary || '',
  }
}

export async function fetchVouchers(websiteId: string): Promise<Voucher[]> {
  const res = await api<{ vouchers: any[] }>(`/websites/${websiteId}/vouchers`)
  return (res?.vouchers || []).map(parseVoucher)
}

export async function createVoucher(websiteId: string, form: VoucherForm): Promise<Voucher> {
  return parseVoucher(
    await api(`/websites/${websiteId}/vouchers`, {
      method: 'POST',
      body: JSON.stringify(voucherPayload(form)),
    })
  )
}

export async function setVoucherActive(id: string, isActive: boolean): Promise<Voucher> {
  return parseVoucher(
    await api(`/vouchers/${id}`, { method: 'PATCH', body: JSON.stringify({ is_active: isActive }) })
  )
}

export function deleteVoucher(id: string): Promise<null> {
  return api<null>(`/vouchers/${id}`, { method: 'DELETE' })
}

function parseLoyalty(raw: any): LoyaltySettings {
  return {
    enabled: !!raw?.enabled,
    points_per_rm: toNumber(raw?.points_per_rm) || 1,
    redeem_points: toNumber(raw?.redeem_points) || 100,
    redeem_value: toNumber(raw?.redeem_value) || 5,
  }
}

export async function fetchLoyalty(websiteId: string): Promise<LoyaltySettings> {
  return parseLoyalty(await api(`/websites/${websiteId}/loyalty`))
}

export async function saveLoyalty(websiteId: string, settings: LoyaltySettings): Promise<LoyaltySettings> {
  return parseLoyalty(
    await api(`/websites/${websiteId}/loyalty`, { method: 'PUT', body: JSON.stringify(settings) })
  )
}

export async function fetchLoyaltyMembers(websiteId: string): Promise<LoyaltyMember[]> {
  const res = await api<{ members: LoyaltyMember[] }>(`/websites/${websiteId}/loyalty/members`)
  return res?.members || []
}

export function adjustLoyaltyPoints(
  websiteId: string,
  customerPhone: string,
  points: number
): Promise<{ customer_phone: string; balance: number }> {
  return api(`/websites/${websiteId}/loyalty/adjust`, {
    method: 'POST',
    body: JSON.stringify({ customer_phone: customerPhone, points }),
  })
}

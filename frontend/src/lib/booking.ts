/**
 * Booking engine client (tempahan slot).
 *
 * Backend: `api/v1/endpoints/bookings.py`. The merchant half goes through
 * `apiFetch` (login token); the customer half is public and uses plain
 * `fetch` so the booking page never touches auth state.
 *
 * All dates here are Malaysian calendar dates ("YYYY-MM-DD") and all times
 * are Malaysian wall-clock times ("HH:MM") — the server does the timezone
 * work, the UI never converts.
 */

import { apiFetch } from '@/lib/api'
import { ensureValidToken } from '@/lib/supabase'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

// ── Types ───────────────────────────────────────────────────────────────

export const WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const
export type Weekday = (typeof WEEKDAYS)[number]

export const WEEKDAY_LABELS: Record<Weekday, string> = {
  mon: 'Isnin',
  tue: 'Selasa',
  wed: 'Rabu',
  thu: 'Khamis',
  fri: 'Jumaat',
  sat: 'Sabtu',
  sun: 'Ahad',
}

export interface HoursRange {
  open: string
  close: string
}

export type WeeklyHours = Record<Weekday, HoursRange[]>

export interface BookingSettings {
  enabled: boolean
  slot_interval_min: number
  capacity_per_slot: number
  lead_time_min: number
  max_days_ahead: number
  weekly_hours: WeeklyHours
  closed_dates: string[]
  note: string
}

export interface BookingService {
  id: string
  name: string
  description: string
  duration_min: number
  price: number | null
  active?: boolean
  sort_order?: number
}

export type ServiceInput = Omit<BookingService, 'id'>

export type BookingStatus = 'pending' | 'confirmed' | 'cancelled' | 'completed' | 'no_show'

export interface OwnerBooking {
  id: string
  reference: string
  service_name: string
  duration_min: number
  price: number | null
  date: string
  time: string | null
  customer_name: string
  customer_phone: string
  notes: string
  status: BookingStatus
  cancelled_by: 'customer' | 'owner' | null
  created_at: string
  next_statuses: BookingStatus[]
}

export interface CustomerBooking {
  reference: string
  service_name: string
  duration_min: number
  price: number | null
  date: string
  time: string | null
  customer_name: string
  customer_phone_masked: string
  notes: string
  status: BookingStatus
  can_cancel: boolean
}

export interface PublicBookingInfo {
  website_id: string
  business_name: string
  enabled: boolean
  services: BookingService[]
  open_weekdays: Weekday[]
  closed_dates: string[]
  max_days_ahead: number
  note: string
  today: string
}

export interface Slot {
  time: string
  available: boolean
}

export interface SlotsResponse {
  date: string
  slots: Slot[]
  reason: string | null
  message: string | null
}

export const STATUS_LABELS: Record<BookingStatus, string> = {
  pending: 'Menunggu',
  confirmed: 'Disahkan',
  cancelled: 'Dibatalkan',
  completed: 'Selesai',
  no_show: 'Tidak hadir',
}

/** The button a merchant presses to move a booking to `status`. */
export const STATUS_ACTION_LABELS: Record<BookingStatus, string> = {
  pending: 'Menunggu',
  confirmed: 'Sahkan',
  cancelled: 'Batalkan',
  completed: 'Tanda selesai',
  no_show: 'Tidak hadir',
}

// ── Pure helpers (tested in booking.test.ts) ────────────────────────────

const pad = (n: number) => String(n).padStart(2, '0')

/** "2026-11-16" + 3 → "2026-11-19". Calendar arithmetic only, no timezone. */
export function addDays(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d + days))
  return `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}`
}

export function weekdayOf(isoDate: string): Weekday {
  const [y, m, d] = isoDate.split('-').map(Number)
  // getUTCDay: 0 = Sunday. WEEKDAYS starts on Monday.
  return WEEKDAYS[(new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7]
}

export interface DateOption {
  date: string
  weekday: Weekday
  /** Closed that weekday, or listed as a closed date. */
  closed: boolean
}

/**
 * The dates a customer may pick: today through `max_days_ahead`, each
 * flagged closed/open. The server re-checks everything; this only keeps
 * the customer from tapping a day that cannot work.
 */
export function bookableDates(
  info: Pick<PublicBookingInfo, 'today' | 'max_days_ahead' | 'open_weekdays' | 'closed_dates'>,
): DateOption[] {
  const open = new Set(info.open_weekdays)
  const closed = new Set(info.closed_dates)
  const out: DateOption[] = []
  for (let i = 0; i <= info.max_days_ahead; i++) {
    const date = addDays(info.today, i)
    const weekday = weekdayOf(date)
    out.push({ date, weekday, closed: !open.has(weekday) || closed.has(date) })
  }
  return out
}

const MONTHS = ['Jan', 'Feb', 'Mac', 'Apr', 'Mei', 'Jun', 'Jul', 'Ogo', 'Sep', 'Okt', 'Nov', 'Dis']

/** "2026-11-16" → "Isnin, 16 Nov 2026" */
export function formatDateMs(isoDate: string): string {
  const [y, m, d] = isoDate.split('-').map(Number)
  if (!y || !m || !d) return isoDate
  return `${WEEKDAY_LABELS[weekdayOf(isoDate)]}, ${d} ${MONTHS[m - 1]} ${y}`
}

/** "14:30" → "2:30 PTG" */
export function formatTime12(hhmm: string | null | undefined): string {
  if (!hhmm) return ''
  const [h, m] = hhmm.split(':').map(Number)
  if (Number.isNaN(h) || Number.isNaN(m)) return hhmm
  const suffix = h < 12 ? 'PG' : 'PTG'
  return `${h % 12 === 0 ? 12 : h % 12}:${pad(m)} ${suffix}`
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} minit`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} jam ${m} minit` : `${h} jam`
}

export function formatPrice(price: number | null | undefined): string {
  if (price === null || price === undefined) return ''
  return `RM${Number(price).toFixed(2)}`
}

/** Loose client-side check; the server normalises and has the final say. */
export function isPlausiblePhone(raw: string): boolean {
  const digits = raw.replace(/\D/g, '')
  return digits.length >= 9 && digits.length <= 13
}

/**
 * What is wrong with a day's opening ranges, or null. Mirrors the server's
 * strict check so the merchant sees the problem before saving.
 */
export function hoursProblem(ranges: HoursRange[]): string | null {
  const re = /^([01]\d|2[0-3]):[0-5]\d$/
  const sorted = [...ranges].sort((a, b) => a.open.localeCompare(b.open))
  for (let i = 0; i < sorted.length; i++) {
    const r = sorted[i]
    if (!re.test(r.open) || !(re.test(r.close) || r.close === '24:00')) return 'Masa tidak sah'
    if (r.close <= r.open) return 'Waktu tutup mesti selepas waktu buka'
    if (i > 0 && r.open < sorted[i - 1].close) return 'Julat masa bertindih'
  }
  return null
}

/** Groups bookings by date, dates ascending, keeping the server's order within a day. */
export function groupByDate<T extends { date: string }>(rows: T[]): Array<{ date: string; rows: T[] }> {
  const map = new Map<string, T[]>()
  for (const row of rows) {
    const list = map.get(row.date)
    if (list) list.push(row)
    else map.set(row.date, [row])
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, list]) => ({ date, rows: list }))
}

// ── Merchant API ────────────────────────────────────────────────────────

export class BookingApiError extends Error {
  code: string
  status: number
  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = 'BookingApiError'
    this.code = code
    this.status = status
  }
}

/** Turns a FastAPI error body into (message, code). Exported for tests. */
export function parseErrorBody(body: unknown, fallback = 'Ralat berlaku. Sila cuba lagi.'): {
  message: string
  code: string
} {
  const detail = (body as any)?.detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    return { message: detail.message || fallback, code: detail.error || 'ERROR' }
  }
  if (typeof detail === 'string') return { message: detail, code: 'ERROR' }
  if (Array.isArray(detail)) return { message: 'Sila semak maklumat yang diisi.', code: 'VALIDATION' }
  return { message: fallback, code: 'ERROR' }
}

/**
 * Authenticated call for the merchant half. Uses the stored token directly
 * so the API's structured errors ({error, message}) survive; a 401 is
 * handed to `apiFetch`, which owns token refresh and the login redirect.
 */
async function adminFetch(path: string, init?: RequestInit): Promise<any> {
  const token = await ensureValidToken()
  if (!token) return apiFetch(path, init)
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    })
  } catch {
    throw new BookingApiError('Tiada sambungan. Sila cuba lagi.', 'NETWORK', 0)
  }
  if (res.status === 401) return apiFetch(path, init)
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const { message, code } = parseErrorBody(body)
    throw new BookingApiError(message, code, res.status)
  }
  return body
}

const admin = (websiteId: string) => `/api/v1/bookings/admin/${websiteId}`

export async function fetchSettings(websiteId: string): Promise<BookingSettings> {
  return (await adminFetch(`${admin(websiteId)}/settings`)).settings
}

export async function saveSettings(websiteId: string, settings: BookingSettings): Promise<BookingSettings> {
  const res = await adminFetch(`${admin(websiteId)}/settings`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  })
  return res.settings
}

export async function fetchServices(websiteId: string): Promise<BookingService[]> {
  return (await adminFetch(`${admin(websiteId)}/services`)).services
}

export function createService(websiteId: string, input: ServiceInput): Promise<BookingService> {
  return adminFetch(`${admin(websiteId)}/services`, { method: 'POST', body: JSON.stringify(input) })
}

export function updateService(websiteId: string, id: string, input: ServiceInput): Promise<BookingService> {
  return adminFetch(`${admin(websiteId)}/services/${id}`, { method: 'PUT', body: JSON.stringify(input) })
}

export function deleteService(websiteId: string, id: string): Promise<{ deleted: boolean }> {
  return adminFetch(`${admin(websiteId)}/services/${id}`, { method: 'DELETE' })
}

export async function fetchBookings(
  websiteId: string,
  opts: { dateFrom?: string; dateTo?: string; status?: BookingStatus | '' } = {},
): Promise<OwnerBooking[]> {
  const q = new URLSearchParams()
  if (opts.dateFrom) q.set('date_from', opts.dateFrom)
  if (opts.dateTo) q.set('date_to', opts.dateTo)
  if (opts.status) q.set('status', opts.status)
  const qs = q.toString()
  return (await adminFetch(`${admin(websiteId)}/bookings${qs ? `?${qs}` : ''}`)).bookings
}

export function setBookingStatus(
  websiteId: string,
  bookingId: string,
  status: BookingStatus,
): Promise<OwnerBooking> {
  return adminFetch(`${admin(websiteId)}/bookings/${bookingId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

// ── Customer API (public) ───────────────────────────────────────────────

async function publicFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}/api/v1/bookings/public/${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    })
  } catch {
    throw new BookingApiError('Tiada sambungan. Sila cuba lagi.', 'NETWORK', 0)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const { message, code } = parseErrorBody(body)
    throw new BookingApiError(message, code, res.status)
  }
  return body as T
}

export const fetchPublicInfo = (websiteId: string) => publicFetch<PublicBookingInfo>(websiteId)

export const fetchSlots = (websiteId: string, serviceId: string, date: string) =>
  publicFetch<SlotsResponse>(
    `${websiteId}/slots?service_id=${encodeURIComponent(serviceId)}&date=${encodeURIComponent(date)}`,
  )

export const createBooking = (
  websiteId: string,
  input: {
    service_id: string
    date: string
    time: string
    customer_name: string
    customer_phone: string
    notes: string
  },
) => publicFetch<CustomerBooking>(websiteId, { method: 'POST', body: JSON.stringify(input) })

export const lookupBooking = (websiteId: string, reference: string, phone: string) =>
  publicFetch<CustomerBooking>(
    `${websiteId}/lookup?reference=${encodeURIComponent(reference)}&phone=${encodeURIComponent(phone)}`,
  )

export const cancelBooking = (websiteId: string, reference: string, phone: string) =>
  publicFetch<CustomerBooking>(`${websiteId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reference, phone }),
  })

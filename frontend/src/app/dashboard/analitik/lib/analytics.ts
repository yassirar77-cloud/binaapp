/**
 * Pure helpers + API types for the Analitik dashboard tab.
 *
 * Everything here is framework-free so it can be unit-tested with vitest.
 * The tier windows MUST mirror the backend's TIER_MAX_DAYS
 * (backend/app/api/v1/endpoints/analytics.py) — the server clamp is the
 * source of truth; these values only drive lock icons in the UI.
 */

export const TIER_MAX_DAYS: Record<string, number> = {
  free: 7,
  starter: 7,
  basic: 30,
  pro: 90,
  enterprise: 90,
}

export const RANGE_OPTIONS = [7, 30, 90] as const
export type RangeDays = (typeof RANGE_OPTIONS)[number]

export function maxDaysForTier(tier: string | null | undefined): number {
  return TIER_MAX_DAYS[(tier || 'free').toLowerCase()] ?? 7
}

export function clampDaysForTier(days: number, tier: string | null | undefined): number {
  return Math.max(1, Math.min(days, maxDaysForTier(tier)))
}

/** Which plan unlocks a given history window (for the upgrade prompt). */
export function requiredTierForDays(days: number): 'basic' | 'pro' | null {
  if (days <= 7) return null
  if (days <= 30) return 'basic'
  return 'pro'
}

export function formatRM(amount: number): string {
  return `RM ${(amount || 0).toLocaleString('ms-MY', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

/** StatCard delta badge props from a percent change (null = no baseline). */
export function deltaBadge(
  changePct: number | null | undefined
): { text: string; color: string; icon: 'up' | 'down' } | undefined {
  if (changePct === null || changePct === undefined) return undefined
  const up = changePct >= 0
  return {
    text: `${up ? '+' : ''}${changePct}%`,
    color: up ? '#C7FF3D' : '#FF5A5F',
    icon: up ? 'up' : 'down',
  }
}

/** '2026-07-03' → '3 Jul' (BM short label for chart axes). */
export function formatDayLabel(dateISO: string): string {
  const d = new Date(`${dateISO}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateISO
  return d.toLocaleDateString('ms-MY', { day: 'numeric', month: 'short' })
}

/* ── API response types (mirror the backend router) ── */

export interface ApiMeta {
  tier: string
  days: number
  max_days: number
  clamped: boolean
}

export interface SummaryBlock {
  revenue?: number
  orders?: number
  change_pct?: number | null
  orders_change_pct?: number | null
  locked?: boolean
}

export interface SummaryResponse extends ApiMeta {
  summary: { today: SummaryBlock; last_7d: SummaryBlock; last_30d: SummaryBlock }
  chats_today: number
  visitors_today: { total_views: number; unique_visitors: number }
}

export interface DailyPoint {
  date: string
  revenue: number
  orders: number
}

export interface HeatmapCell {
  dow: number
  hour: number
  count: number
}

export interface TopItem {
  item_name: string
  quantity: number
  revenue: number
}

export interface ZoneRow {
  zone: string
  orders: number
  cancelled: number
  revenue: number
  delivery_fees: number
  cancel_rate_pct: number
}

export interface RiderRow {
  rider_id: string
  name: string
  deliveries: number
  rating: number | null
  total_deliveries_all_time: number | null
  avg_delivery_minutes: number | null
}

export interface ChatResponse extends ApiMeta {
  series: { date: string; conversations: number }[]
  total_conversations: number
  total_messages: number
}

export interface VisitorsResponse extends ApiMeta {
  series: { date: string; total_views: number; unique_visitors: number }[]
  totals: { total_views: number; unique_visitors: number }
  devices: { mobile: number; tablet: number; desktop: number }
  top_pages: { page_path: string; views: number }[]
  top_referrers: { source: string; views: number }[]
}

/* ── Heatmap shaping ── */

export const DOW_LABELS_BM = ['Isn', 'Sel', 'Rab', 'Kha', 'Jum', 'Sab', 'Ahd']

export interface HeatmapGrid {
  /** rows[dow][hour] = count */
  rows: number[][]
  max: number
}

export function buildHeatmapGrid(cells: HeatmapCell[]): HeatmapGrid {
  const rows: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))
  let max = 0
  for (const c of cells || []) {
    if (c.dow >= 0 && c.dow < 7 && c.hour >= 0 && c.hour < 24) {
      rows[c.dow][c.hour] = c.count
      if (c.count > max) max = c.count
    }
  }
  return { rows, max }
}

/** Lime opacity for a heatmap cell (0 stays visibly "off"). */
export function heatmapOpacity(count: number, max: number): number {
  if (count <= 0 || max <= 0) return 0
  return 0.15 + 0.85 * (count / max)
}

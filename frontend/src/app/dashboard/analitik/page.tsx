'use client'

/**
 * Analitik — merchant analytics dashboard.
 *
 * All order/chat/visitor data comes from the authenticated backend
 * analytics API (/api/v1/analytics/*, service role) — never from direct
 * browser Supabase reads (see migration 049). History depth is clamped
 * server-side by plan; the UI mirrors the clamp with lock states and
 * upgrade prompts.
 */

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'

import DashboardHeader from '@/components/dashboard-new/DashboardHeader'
import { UpgradeModal } from '@/components/UpgradeModal'
import { useSubscriptionStatus } from '@/hooks/useSubscriptionStatus'
import { apiFetch } from '@/lib/api'
import { getCurrentUser, getStoredToken, signOut, supabase } from '@/lib/supabase'

import AnalitikEmptyState from './components/AnalitikEmptyState'
import ChatVolumeCard from './components/ChatVolumeCard'
import ExportButton from './components/ExportButton'
import KpiRow from './components/KpiRow'
import OrdersHeatmap from './components/OrdersHeatmap'
import RangePicker from './components/RangePicker'
import { RiderTable, ZoneTable } from './components/Tables'
import TopItems from './components/TopItems'
import VisitorsCard from './components/VisitorsCard'
import {
  clampDaysForTier,
  requiredTierForDays,
  type ChatResponse,
  type DailyPoint,
  type HeatmapCell,
  type RangeDays,
  type RiderRow,
  type SummaryResponse,
  type TopItem,
  type VisitorsResponse,
  type ZoneRow,
} from './lib/analytics'

import '@/components/dashboard-new/dashboard.css'

// RevenueChart pulls in recharts (heavy) — load it lazily so the analytics
// page shell paints immediately and the chart streams in after.
const RevenueChart = dynamic(() => import('./components/RevenueChart'), {
  ssr: false,
  loading: () => <div style={{ height: 280 }} className="animate-pulse bg-gray-100 rounded-xl" />,
})

interface WebsiteOption {
  id: string
  label: string
  status: string | null
}

interface AnalyticsData {
  summary: SummaryResponse | null
  revenueDaily: DailyPoint[]
  heatmap: HeatmapCell[]
  topItems: TopItem[]
  zones: ZoneRow[]
  riders: RiderRow[]
  chat: ChatResponse | null
  visitors: VisitorsResponse | null
}

const EMPTY_DATA: AnalyticsData = {
  summary: null,
  revenueDaily: [],
  heatmap: [],
  topItems: [],
  zones: [],
  riders: [],
  chat: null,
  visitors: null,
}

export default function AnalitikPage() {
  const router = useRouter()
  const { tier, isLoading: subLoading } = useSubscriptionStatus()
  // While the subscription status is still loading the hook reports the
  // default 'starter', which would flash 30/90-day locks (and open the
  // wrong upgrade modal) for a Basic/Pro merchant. Stay permissive until
  // it resolves — the server clamps history regardless, so this is only UI.
  const gateTier = subLoading ? 'pro' : tier

  const [userName, setUserName] = useState('Pengguna')
  const [websites, setWebsites] = useState<WebsiteOption[]>([])
  const [websiteId, setWebsiteId] = useState<string>('')
  const [days, setDays] = useState<RangeDays>(7)
  const [data, setData] = useState<AnalyticsData>(EMPTY_DATA)
  const [loading, setLoading] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [error, setError] = useState('')
  const [upgradeTarget, setUpgradeTarget] = useState<string | null>(null)

  // ── Load user + website list (websites table is not RLS-blocked) ──
  useEffect(() => {
    const load = async () => {
      const token = getStoredToken()
      const user = await getCurrentUser()
      if (!token || !user) {
        router.push('/login')
        return
      }
      setUserName((user as any).user_metadata?.full_name || user.email || 'Pengguna')

      if (!supabase) {
        setError('Ralat sambungan. Sila cuba lagi.')
        setLoading(false)
        return
      }
      const { data: rows, error: sbError } = await supabase
        .from('websites')
        .select('id, business_name, subdomain, status')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })

      if (sbError) {
        setError('Gagal memuatkan senarai website.')
        setLoading(false)
        return
      }
      const options: WebsiteOption[] = (rows || []).map((w: any) => ({
        id: w.id,
        label: w.business_name || w.subdomain || 'Website',
        status: w.status,
      }))
      setWebsites(options)
      // Read ?website= directly (avoids useSearchParams' Suspense requirement)
      const requested =
        typeof window !== 'undefined'
          ? new URLSearchParams(window.location.search).get('website')
          : null
      const initial =
        options.find((o) => o.id === requested)?.id || options[0]?.id || ''
      setWebsiteId(initial)
      setLoading(false)
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Fetch analytics whenever website/range changes ──
  // `stale` guards against out-of-order responses: if the user switches
  // website/range mid-flight, the superseded run must not call setData.
  useEffect(() => {
    if (!websiteId) return
    let stale = false
    const run = async () => {
      setLoadingData(true)
      setError('')
      const q = `website_id=${websiteId}&days=${days}`
      try {
        const results = await Promise.allSettled([
          apiFetch(`/api/v1/analytics/summary?website_id=${websiteId}`),
          apiFetch(`/api/v1/analytics/revenue-daily?${q}`),
          apiFetch(`/api/v1/analytics/orders-heatmap?${q}`),
          apiFetch(`/api/v1/analytics/top-items?${q}`),
          apiFetch(`/api/v1/analytics/zones?${q}`),
          apiFetch(`/api/v1/analytics/riders?${q}`),
          apiFetch(`/api/v1/analytics/chat?${q}`),
          apiFetch(`/api/v1/analytics/visitors?${q}`),
        ])
        if (stale) return
        const [summary, revenue, heatmap, topItems, zones, riders, chat, visitors] = results
        const val = <T,>(r: PromiseSettledResult<any>, fallback: T, pick?: string): T => {
          if (r.status !== 'fulfilled') return fallback
          return pick ? (r.value?.[pick] ?? fallback) : (r.value ?? fallback)
        }
        setData({
          summary: val<SummaryResponse | null>(summary, null),
          revenueDaily: val<DailyPoint[]>(revenue, [], 'series'),
          heatmap: val<HeatmapCell[]>(heatmap, [], 'cells'),
          topItems: val<TopItem[]>(topItems, [], 'items'),
          zones: val<ZoneRow[]>(zones, [], 'zones'),
          riders: val<RiderRow[]>(riders, [], 'riders'),
          chat: val<ChatResponse | null>(chat, null),
          visitors: val<VisitorsResponse | null>(visitors, null),
        })
        // Surface an error if everything failed, or if the KPI band itself
        // failed (its absence is otherwise indistinguishable from "no data").
        if (results.every((r) => r.status === 'rejected')) {
          setError('Gagal memuatkan data analitik. Sila cuba lagi.')
        } else if (summary.status === 'rejected') {
          setError('Sebahagian data tidak dapat dimuatkan. Sila muat semula.')
        }
      } finally {
        if (!stale) setLoadingData(false)
      }
    }
    run()
    return () => {
      stale = true
    }
  }, [websiteId, days])

  // Keep the selected range within the plan window (e.g. after downgrade)
  useEffect(() => {
    const clamped = clampDaysForTier(days, tier)
    if (clamped !== days) setDays(clamped as RangeDays)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tier])

  const openUpgradeFor = (lockedDays: number) => {
    setUpgradeTarget(requiredTierForDays(lockedDays) || 'basic')
  }

  return (
    <div className="dash-bg min-h-screen font-geist">
      <div className="dash-dotgrid" />
      <div className="dash-glow-top" />
      <DashboardHeader userName={userName} onLogout={() => signOut()} />

      <main className="relative mx-auto max-w-7xl px-4 lg:px-6 py-6 space-y-5">
        {/* Page header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-white tracking-tight">Analitik</h1>
            <p className="text-[13px] text-white/40 mt-0.5">
              Prestasi jualan, penghantaran dan pelawat website anda
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            {websites.length > 1 && (
              <select
                value={websiteId}
                onChange={(e) => setWebsiteId(e.target.value)}
                className="rounded-full bg-white/[0.05] border border-white/[0.08] px-3.5 py-1.5 text-xs text-white/80 focus:outline-none focus:border-[#C7FF3D]/50"
              >
                {websites.map((w) => (
                  <option key={w.id} value={w.id} className="bg-[#161623]">
                    {w.label}
                  </option>
                ))}
              </select>
            )}
            <RangePicker
              value={days}
              tier={gateTier}
              onChange={setDays}
              onLockedClick={openUpgradeFor}
            />
            {websiteId && (
              <ExportButton
                websiteId={websiteId}
                days={days}
                tier={gateTier}
                onLockedClick={() => setUpgradeTarget('pro')}
              />
            )}
          </div>
        </div>

        {/* Body */}
        {loading ? (
          <div className="flex items-center justify-center py-32">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
          </div>
        ) : websites.length === 0 ? (
          <div className="dash-surface">
            <AnalitikEmptyState
              heading="Anda belum mempunyai website"
              sub="Bina website pertama anda untuk mula melihat analitik di sini."
            />
          </div>
        ) : (
          <div className={loadingData ? 'opacity-60 pointer-events-none transition-opacity' : 'transition-opacity'}>
            {error && (
              <div className="mb-4 rounded-xl border border-[#FF5A5F]/30 bg-[#FF5A5F]/10 px-4 py-3 text-[13px] text-[#FF9A9D]">
                {error}
              </div>
            )}

            <div className="space-y-5">
              {data.summary && <KpiRow summary={data.summary} />}

              <RevenueChart series={data.revenueDaily} />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <OrdersHeatmap cells={data.heatmap} />
                <TopItems items={data.topItems} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <ZoneTable zones={data.zones} />
                <RiderTable riders={data.riders} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {data.chat && <ChatVolumeCard chat={data.chat} />}
                {data.visitors && <VisitorsCard visitors={data.visitors} />}
              </div>
            </div>
          </div>
        )}
      </main>

      <UpgradeModal
        show={upgradeTarget !== null}
        currentTier={tier}
        targetTier={upgradeTarget || 'basic'}
        onClose={() => setUpgradeTarget(null)}
      />
    </div>
  )
}

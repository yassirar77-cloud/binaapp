'use client'

import StatCard from '@/components/dashboard-new/StatCard'

import { deltaBadge, formatRM, type SummaryResponse } from '../lib/analytics'

/** Top KPI band: today's sales (featured), today's orders, 7-day sales,
 *  today's visitors. All values come pre-aggregated from the backend. */
export default function KpiRow({ summary }: { summary: SummaryResponse }) {
  const today = summary.summary.today
  const last7 = summary.summary.last_7d

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <StatCard
        label="Jualan Hari Ini"
        value={formatRM(today.revenue ?? 0)}
        delta={deltaBadge(today.change_pct)}
        subtitle="berbanding semalam"
        variant="featured"
      />
      <StatCard
        label="Pesanan Hari Ini"
        value={String(today.orders ?? 0)}
        subtitle={`${summary.chats_today} perbualan chat hari ini`}
      />
      <StatCard
        label="Jualan 7 Hari"
        value={formatRM(last7.revenue ?? 0)}
        delta={deltaBadge(last7.change_pct)}
        subtitle={`${last7.orders ?? 0} pesanan · berbanding 7 hari sebelumnya`}
      />
      <StatCard
        label="Pelawat Hari Ini"
        value={String(summary.visitors_today.unique_visitors ?? 0)}
        subtitle={`${summary.visitors_today.total_views ?? 0} paparan halaman`}
      />
    </div>
  )
}

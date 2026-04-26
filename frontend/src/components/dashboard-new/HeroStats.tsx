'use client'

import { ReactElement, ReactNode } from 'react'
import StatCard from './StatCard'
import Sparkline from './Sparkline'

/* ── Prop types ── */

export interface SalesData {
  amount: string
  currencyPrefix?: string
  deltaPercent: string
  deltaDirection: 'up' | 'down'
  barPoints: { value: number; label?: string }[]
  dayLabels: string[]
}

export interface OrdersData {
  count: number
  statusBreakdown: { label: string; count: number; color: string }[]
  onViewAll?: () => void
}

export interface CommissionData {
  amount: string
  currencyPrefix?: string
  subtitle: string
  calcLine1: string
  calcLine2: string
  ytdLabel: string
  ytdAmount: string
}

export interface WebsitesData {
  active: number
  limit: number
  planName: string
  onCreateNew?: () => void
  onUpgradePlan?: () => void
}

interface HeroStatsProps {
  sales: SalesData
  orders: OrdersData
  commission: CommissionData
  websites: WebsitesData
}

export default function HeroStats({
  sales,
  orders,
  commission,
  websites,
}: HeroStatsProps): ReactElement {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-8">
      <SalesCard data={sales} />
      <OrdersCard data={orders} />
      <CommissionCard data={commission} />
      <WebsitesCard data={websites} />
    </div>
  )
}

/* ── Sales stat ── */

function SalesCard({ data }: { data: SalesData }): ReactElement {
  return (
    <StatCard
      label="Jualan Hari Ini"
      value={
        <>
          <span className="text-xl text-ink-400 font-medium mr-1 tracking-[-0.02em]">
            {data.currencyPrefix ?? 'RM'}
          </span>
          {data.amount}
        </>
      }
      delta={{
        text: data.deltaPercent,
        color: '#C7FF3D',
        icon: data.deltaDirection,
      }}
      footer={
        <div className="flex justify-between items-end">
          <div>
            <div className="dash-eyebrow text-[9px] text-[#4A4A5C] tracking-[0.1em] mb-1">
              7 hari lepas
            </div>
            <div className="flex gap-3.5 font-geist-mono text-[10px] text-ink-400">
              {data.dayLabels.map((d, i) => (
                <span
                  key={d}
                  className={
                    i === data.dayLabels.length - 1 ? 'text-volt-400' : ''
                  }
                >
                  {d}
                </span>
              ))}
            </div>
          </div>
          <Sparkline points={data.barPoints} />
        </div>
      }
    />
  )
}

/* ── Orders stat ── */

function OrdersCard({ data }: { data: OrdersData }): ReactElement {
  return (
    <StatCard
      label="Pesanan Baru"
      pulse
      value={
        <span className="text-[56px] tracking-[-0.045em]">{data.count}</span>
      }
      subtitle={
        <>
          menunggu{' '}
          <span className="text-err-400 font-medium">pengesahan</span>
        </>
      }
      footer={
        <div className="flex justify-between items-center">
          <div className="flex gap-3 font-geist-mono text-[10px]">
            {data.statusBreakdown.map((s) => (
              <span key={s.label} className="text-ink-400">
                {s.label}{' '}
                <span style={{ color: s.color }}>{s.count}</span>
              </span>
            ))}
          </div>
          {data.onViewAll && (
            <button
              onClick={data.onViewAll}
              className="font-geist text-xs text-brand-300 font-medium flex items-center gap-1 hover:text-brand-200 transition-colors bg-transparent border-0 cursor-pointer p-0"
            >
              Lihat semua
              <ArrowRightSmall />
            </button>
          )}
        </div>
      }
    />
  )
}

/* ── Commission stat (featured) ── */

function CommissionCard({ data }: { data: CommissionData }): ReactElement {
  return (
    <StatCard
      variant="featured"
      label="★ Komisen Dijimatkan"
      labelColor="#C7FF3D"
      value={
        <>
          <span className="text-[22px] text-volt-400/65 font-medium mr-1 tracking-[-0.02em]">
            {data.currencyPrefix ?? 'RM'}
          </span>
          {data.amount}
        </>
      }
      subtitle={
        <span className="text-brand-100">{data.subtitle}</span>
      }
      footer={
        <div className="flex justify-between items-center">
          <div className="font-geist-mono text-[10px] text-brand-300 leading-relaxed">
            <div>{data.calcLine1}</div>
            <div className="text-ink-400">{data.calcLine2}</div>
          </div>
          <div className="font-geist-mono text-[10px] text-ink-400 text-right leading-relaxed">
            {data.ytdLabel}
            <br />
            <span className="text-volt-400 text-[13px] font-semibold">
              {data.ytdAmount}
            </span>
          </div>
        </div>
      }
    />
  )
}

/* ── Websites stat ── */

function WebsitesCard({ data }: { data: WebsitesData }): ReactElement {
  const pips = Array.from({ length: data.limit }, (_, i) => i)

  return (
    <StatCard
      label="Website Aktif"
      value={
        <span className="flex items-baseline gap-2">
          <span className="text-[56px] tracking-[-0.045em]">{data.active}</span>
          <span className="font-geist-mono text-sm text-ink-400 font-medium">
            / {data.limit}
          </span>
        </span>
      }
      subtitle={
        <>
          dibenarkan pada plan{' '}
          <span className="text-brand-300 font-medium">{data.planName}</span>
        </>
      }
      footer={
        <>
          {/* Segmented progress bar */}
          <div className="flex gap-0.5 h-1 rounded-full overflow-hidden mb-3.5">
            {pips.map((i) => (
              <div
                key={i}
                className="flex-1 rounded-full"
                style={{
                  background:
                    i < data.active
                      ? '#4F3DFF'
                      : 'rgba(255,255,255,0.05)',
                }}
              />
            ))}
          </div>
          <div className="flex justify-between items-center">
            {data.onCreateNew && (
              <button
                onClick={data.onCreateNew}
                className="font-geist text-xs text-brand-300 font-medium flex items-center gap-1 hover:text-brand-200 transition-colors bg-transparent border-0 cursor-pointer p-0"
              >
                <PlusSmall /> Bina baru
              </button>
            )}
            {data.onUpgradePlan && (
              <button
                onClick={data.onUpgradePlan}
                className="font-geist text-xs text-ink-400 hover:text-ink-300 transition-colors bg-transparent border-0 cursor-pointer p-0"
              >
                Naik taraf plan →
              </button>
            )}
          </div>
        </>
      }
    />
  )
}

/* ── Tiny inline icons ── */

function ArrowRightSmall(): ReactElement {
  return (
    <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

function PlusSmall(): ReactElement {
  return (
    <svg width={12} height={12} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

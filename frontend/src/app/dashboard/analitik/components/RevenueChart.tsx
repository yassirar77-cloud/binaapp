'use client'

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { formatDayLabel, formatRM, type DailyPoint } from '../lib/analytics'
import AnalitikEmptyState from './AnalitikEmptyState'

const VOLT = '#C7FF3D'

/** Daily revenue area chart (volt on ink), zero-filled by the backend. */
export default function RevenueChart({ series }: { series: DailyPoint[] }) {
  const hasData = series.some((p) => p.revenue > 0 || p.orders > 0)

  return (
    <div className="dash-surface p-5">
      <div className="dash-eyebrow mb-4">Jualan Harian</div>
      {!hasData ? (
        <AnalitikEmptyState
          heading="Tiada jualan dalam tempoh ini"
          sub="Carta jualan harian anda akan muncul di sini selepas pesanan pertama."
        />
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="voltFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={VOLT} stopOpacity={0.28} />
                  <stop offset="100%" stopColor={VOLT} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDayLabel}
                tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis
                tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={52}
                tickFormatter={(v: number) => `RM${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: '#161623',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 10,
                  fontSize: 12,
                }}
                labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
                labelFormatter={(label: string) => formatDayLabel(label)}
                formatter={(value: number, name: string) =>
                  name === 'revenue'
                    ? [formatRM(value), 'Jualan']
                    : [String(value), 'Pesanan']
                }
              />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke={VOLT}
                strokeWidth={2}
                fill="url(#voltFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

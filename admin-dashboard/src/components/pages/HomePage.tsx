'use client'

import { useState, useEffect, useCallback } from 'react'
import { StatCard, Card, LoadingSpinner } from '@/components/ui/Card'
import { formatCurrency } from '@/lib/utils'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

type Stats = {
  totalUsers: number
  weekUsers: number
  revenueMTD: number
  revenueWeek: number
  totalWebsites: number
  successRate: string
  errorsToday: number
  deepseekFails: number
  qwenFails: number
}

type ChartData = {
  signupChart: { date: string; label: string; count: number }[]
  revenueChart: { date: string; label: string; amount: number }[]
}

export function HomePage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [charts, setCharts] = useState<ChartData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, chartsRes] = await Promise.all([
        fetch('/api/stats'),
        fetch('/api/stats/charts'),
      ])
      const statsData = await statsRes.json()
      const chartsData = await chartsRes.json()
      setStats(statsData)
      setCharts(chartsData)
    } catch (err) {
      console.error('Failed to fetch data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000) // Auto-refresh every 10s
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) return <LoadingSpinner />

  if (!stats) {
    return <div className="text-center py-12 text-gray-500">Failed to load data</div>
  }

  return (
    <div className="space-y-4">
      {/* Stats Cards - 2x2 grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          icon="&#x1F465;"
          label="Total Users"
          value={stats.totalUsers.toLocaleString()}
          subValue={`+${stats.weekUsers} this week`}
          subColor="text-green-400"
        />
        <StatCard
          icon="&#x1F4B0;"
          label="Revenue (MTD)"
          value={formatCurrency(stats.revenueMTD)}
          subValue={`+${formatCurrency(stats.revenueWeek)} this week`}
          subColor="text-green-400"
        />
        <StatCard
          icon="&#x1F310;"
          label="Websites Made"
          value={stats.totalWebsites.toLocaleString()}
          subValue={`${stats.successRate}% success rate`}
        />
        <StatCard
          icon="&#x274C;"
          label="Errors Today"
          value={stats.errorsToday}
          subValue={
            stats.errorsToday > 0
              ? `${stats.deepseekFails} DeepSeek, ${stats.qwenFails} Qwen`
              : 'All clear'
          }
          subColor={stats.errorsToday > 0 ? 'text-red-400' : 'text-green-400'}
        />
      </div>

      {/* User Registration Chart */}
      {charts && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">New Users (Last 30 Days)</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={charts.signupChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                  interval={6}
                  axisLine={{ stroke: '#374151' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '12px',
                    fontSize: '12px',
                    color: '#f9fafb',
                  }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#ea580c"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, fill: '#ea580c' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Revenue Chart */}
      {charts && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Daily Revenue (Last 30 Days)</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts.revenueChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                  interval={6}
                  axisLine={{ stroke: '#374151' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `RM${v}`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '12px',
                    fontSize: '12px',
                    color: '#f9fafb',
                  }}
                  labelStyle={{ color: '#9ca3af' }}
                  formatter={(value: number) => [`RM ${value.toFixed(2)}`, 'Revenue']}
                />
                <Bar
                  dataKey="amount"
                  fill="#ea580c"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={20}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </div>
  )
}

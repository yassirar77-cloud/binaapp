'use client'

import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Card, Badge, LoadingSpinner, EmptyState } from '@/components/ui/Card'
import { formatCurrency, formatDateTime } from '@/lib/utils'
import { apiFetch } from '@/lib/api-fetch'
import {
  PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, Legend,
} from 'recharts'

type RevenueData = {
  today: number
  week: number
  month: number
  allTime: number
  byPlan: Record<string, number>
  transactions: {
    id: string
    amount: number
    description: string
    type: string
    status: string
    created_at: string
    user_name: string
  }[]
}

const PLAN_COLORS: Record<string, string> = {
  starter: '#22c55e',
  basic: '#3b82f6',
  pro: '#ea580c',
  addon: '#eab308',
  other: '#6b7280',
}

export function RevenuePage() {
  const [data, setData] = useState<RevenueData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await apiFetch('/api/revenue')
      if (!res.ok) throw new Error(`Revenue request failed (${res.status})`)
      const json = await res.json()
      if (!json || typeof json !== 'object' || !Array.isArray(json.transactions)) {
        throw new Error('Unexpected revenue payload')
      }
      setData({
        ...json,
        byPlan: json.byPlan && typeof json.byPlan === 'object' ? json.byPlan : {},
      })
    } catch (err) {
      console.error('Failed to fetch revenue:', err)
      toast.error('Failed to load revenue data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) return <LoadingSpinner />
  if (!data) return <EmptyState message="Failed to load revenue data" />

  const pieData = Object.entries(data.byPlan ?? {})
    .filter(([, v]) => Number(v) > 0)
    .map(([plan, amount]) => ({
      name: plan.charAt(0).toUpperCase() + plan.slice(1),
      value: amount,
      color: PLAN_COLORS[plan] || PLAN_COLORS.other,
    }))

  // payments: 'paid'/'successful'; transactions: 'success'; addon credits: 'active'/'depleted'
  const PAID_STATUSES = ['paid', 'successful', 'success', 'active', 'depleted']

  const statusColor = (s: string): 'green' | 'yellow' | 'red' | 'gray' => {
    if (PAID_STATUSES.includes(s)) return 'green'
    switch (s) {
      case 'pending': return 'yellow'
      case 'failed': return 'red'
      default: return 'gray'
    }
  }

  const statusLabel = (s: string): string => {
    if (PAID_STATUSES.includes(s)) return 'Paid'
    switch (s) {
      case 'pending': return 'Pending'
      case 'failed': return 'Failed'
      default: return s
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white">Revenue</h2>

      {/* Revenue Summary */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Revenue Summary</h3>
        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-sm text-gray-400">Today</span>
            <span className="text-sm font-semibold text-white">{formatCurrency(Number(data.today) || 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-gray-400">This Week</span>
            <span className="text-sm font-semibold text-white">{formatCurrency(Number(data.week) || 0)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-gray-400">This Month</span>
            <span className="text-sm font-semibold text-white">{formatCurrency(Number(data.month) || 0)}</span>
          </div>
          <div className="flex justify-between border-t border-gray-800 pt-3">
            <span className="text-sm text-gray-400">All Time</span>
            <span className="text-lg font-bold text-brand-orange">{formatCurrency(Number(data.allTime) || 0)}</span>
          </div>
        </div>
      </Card>

      {/* Revenue by Plan */}
      {pieData.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Revenue by Plan</h3>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  dataKey="value"
                  paddingAngle={2}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '12px',
                    fontSize: '12px',
                    color: '#f9fafb',
                  }}
                  formatter={(value: number) => [formatCurrency(value), 'Revenue']}
                />
                <Legend
                  wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Payment History */}
      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Payment History</h3>
        {(data.transactions ?? []).length === 0 ? (
          <EmptyState message="No transactions yet" />
        ) : (
          <div className="space-y-2">
            {(data.transactions ?? []).map(t => (
              <Card key={t.id}>
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-white">
                      {formatCurrency(Number(t.amount) || 0)} &mdash; {t.user_name}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {t.description || t.type} &bull; {formatDateTime(t.created_at)}
                    </p>
                  </div>
                  <Badge color={statusColor(t.status)}>
                    {statusLabel(t.status)}
                  </Badge>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

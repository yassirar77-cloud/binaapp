'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getStoredToken } from '@/lib/supabase'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface MonitorEvent {
  id: string
  event_type: string
  description: string
  severity: string
  details?: Record<string, unknown>
  action_taken?: string
  action_details?: string
  credit_awarded?: number
  acknowledged: boolean
  created_at: string
}

interface RestaurantHealth {
  id: string
  website_id: string
  total_orders: number
  completed_orders: number
  cancelled_orders: number
  disputed_orders: number
  fulfillment_rate: number
  complaint_rate: number
  health_status: string
  updated_at: string
}

interface Summary {
  total_unread: number
  critical: number
  warning: number
  info: number
  restaurant_health: RestaurantHealth[]
}

const EVENT_TYPE_INFO: Record<string, { icon: string; label: string }> = {
  website_down: { icon: '🔴', label: 'Laman Web Tidak Aktif' },
  website_slow: { icon: '🟡', label: 'Laman Web Perlahan' },
  website_broken: { icon: '🔧', label: 'Laman Web Rosak' },
  payment_failed: { icon: '💳', label: 'Pembayaran Gagal' },
  payment_webhook_missing: { icon: '🔗', label: 'Webhook Hilang' },
  delivery_stalled: { icon: '🚫', label: 'Penghantaran Terhenti' },
  delivery_no_rider: { icon: '🏍️', label: 'Tiada Rider' },
  order_stuck: { icon: '📦', label: 'Pesanan Tersekat' },
  order_no_response: { icon: '⏰', label: 'Tiada Respons' },
  high_complaint_rate: { icon: '📊', label: 'Kadar Aduan Tinggi' },
  subscription_expiring: { icon: '⏳', label: 'Langganan Hampir Tamat' },
  storage_limit: { icon: '💾', label: 'Had Storan' },
  unusual_activity: { icon: '⚠️', label: 'Aktiviti Luar Biasa' },
}

const SEVERITY_COLORS: Record<string, string> = {
  info: 'border-blue-200 bg-blue-50',
  warning: 'border-yellow-200 bg-yellow-50',
  critical: 'border-red-200 bg-red-50',
}

const SEVERITY_BADGE: Record<string, string> = {
  info: 'bg-blue-100 text-blue-700',
  warning: 'bg-yellow-100 text-yellow-700',
  critical: 'bg-red-100 text-red-700',
}

const HEALTH_STATUS_COLORS: Record<string, string> = {
  healthy: 'text-green-700 bg-green-100',
  warning: 'text-yellow-700 bg-yellow-100',
  critical: 'text-red-700 bg-red-100',
  suspended: 'text-gray-700 bg-gray-200',
}

export default function MonitorPage() {
  const router = useRouter()
  const [events, setEvents] = useState<MonitorEvent[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState<string>('')
  const [filterSeverity, setFilterSeverity] = useState<string>('')

  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    const token = getStoredToken()
    if (!token) {
      router.push('/login?redirect=/monitor')
      throw new Error('Not authenticated')
    }
    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      ...options,
    })
    if (res.status === 401) {
      router.push('/login?redirect=/monitor')
      throw new Error('Session expired')
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Request failed')
    }
    return res.json()
  }, [router])

  const loadEvents = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (filterType) params.set('event_type', filterType)
      if (filterSeverity) params.set('severity', filterSeverity)

      const data = await apiFetch(`/api/v1/monitor/events?${params}`)
      setEvents(data.events || [])
    } catch (err) {
      console.error('Failed to load events:', err)
    }
  }, [apiFetch, filterType, filterSeverity])

  const loadSummary = useCallback(async () => {
    try {
      const data = await apiFetch('/api/v1/monitor/summary')
      setSummary(data)
    } catch (err) {
      console.error('Failed to load summary:', err)
    }
  }, [apiFetch])

  useEffect(() => {
    async function load() {
      await Promise.all([loadEvents(), loadSummary()])
      setLoading(false)
    }
    load()
  }, [loadEvents, loadSummary])

  useEffect(() => {
    loadEvents()
  }, [filterType, filterSeverity, loadEvents])

  const handleAcknowledge = async (eventId: string) => {
    try {
      await apiFetch(`/api/v1/monitor/events/${eventId}/acknowledge`, { method: 'POST' })
      setEvents((prev) => prev.map((e) => e.id === eventId ? { ...e, acknowledged: true } : e))
      loadSummary()
    } catch (err) {
      console.error('Failed to acknowledge:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Memuatkan...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-800">Pemantauan AI</h1>
            <p className="text-xs text-gray-500">Notifikasi &amp; pemantauan platform</p>
          </div>
          <Link href="/profil" className="text-sm text-blue-600 hover:underline">
            Kembali ke Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Summary cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white border rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-gray-800">{summary.total_unread}</p>
              <p className="text-xs text-gray-500">Belum Dibaca</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-red-700">{summary.critical}</p>
              <p className="text-xs text-red-600">Kritikal</p>
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-yellow-700">{summary.warning}</p>
              <p className="text-xs text-yellow-600">Amaran</p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-blue-700">{summary.info}</p>
              <p className="text-xs text-blue-600">Maklumat</p>
            </div>
          </div>
        )}

        {/* Restaurant health */}
        {summary?.restaurant_health && summary.restaurant_health.length > 0 && (
          <div className="bg-white border rounded-xl p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Kesihatan Restoran</h2>
            <div className="space-y-3">
              {summary.restaurant_health.map((rh) => (
                <div key={rh.id} className="flex items-center justify-between border-b pb-2 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${HEALTH_STATUS_COLORS[rh.health_status] || ''}`}>
                      {rh.health_status}
                    </span>
                    <div>
                      <p className="text-sm text-gray-700">
                        {rh.total_orders} pesanan | {rh.completed_orders} selesai
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-700">{rh.fulfillment_rate}%</p>
                    <p className="text-xs text-gray-400">kadar pemenuhan</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-3 flex-wrap">
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:border-blue-400"
          >
            <option value="">Semua Tahap</option>
            <option value="critical">Kritikal</option>
            <option value="warning">Amaran</option>
            <option value="info">Maklumat</option>
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:border-blue-400"
          >
            <option value="">Semua Jenis</option>
            {Object.entries(EVENT_TYPE_INFO).map(([key, info]) => (
              <option key={key} value={key}>{info.label}</option>
            ))}
          </select>
        </div>

        {/* Events list */}
        <div className="space-y-3">
          {events.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p>Tiada peristiwa pemantauan.</p>
            </div>
          ) : (
            events.map((event) => {
              const typeInfo = EVENT_TYPE_INFO[event.event_type] || { icon: '📌', label: event.event_type }
              return (
                <div
                  key={event.id}
                  className={`border rounded-xl p-4 ${SEVERITY_COLORS[event.severity] || 'bg-white'} ${
                    event.acknowledged ? 'opacity-60' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <span className="text-xl">{typeInfo.icon}</span>
                      <div>
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-medium text-gray-800">{typeInfo.label}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${SEVERITY_BADGE[event.severity] || ''}`}>
                            {event.severity}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">{event.description}</p>
                        {event.action_taken && (
                          <p className="text-xs text-gray-400 mt-1">
                            Tindakan: {event.action_taken}
                            {event.credit_awarded ? ` | +RM${event.credit_awarded}` : ''}
                          </p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(event.created_at).toLocaleString('ms-MY')}
                        </p>
                      </div>
                    </div>
                    {!event.acknowledged && (
                      <button
                        onClick={() => handleAcknowledge(event.id)}
                        className="text-xs px-3 py-1 bg-white border rounded-lg text-gray-600 hover:bg-gray-50 transition-colors flex-shrink-0"
                      >
                        Tandakan Dibaca
                      </button>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </main>
    </div>
  )
}

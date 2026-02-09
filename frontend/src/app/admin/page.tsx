'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getStoredToken } from '@/lib/supabase'
import AdminStatCard from '@/components/admin/AdminStatCard'
import EscalatedDisputeCard from '@/components/admin/EscalatedDisputeCard'
import ChatViewer from '@/components/admin/ChatViewer'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface DashboardStats {
  total_users: number
  active_subscriptions: number
  total_disputes_today: number
  escalated_disputes: number
  ai_resolution_rate: number
  total_credits_awarded_today: number
  active_support_chats: number
  escalated_chats: number
  websites_unhealthy: number
  monitor_events_unacknowledged: number
}

interface Dispute {
  id: string
  order_id?: string
  user_id?: string
  category?: string
  description?: string
  status: string
  ai_reasoning?: string
  confidence_score?: number
  recommended_action?: string
  credit_amount?: number
  created_at?: string
  evidence_urls?: string[]
}

interface Chat {
  id: string
  user_id: string
  title?: string
  status: string
  category?: string
  created_at?: string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  image_urls?: string[]
  action_taken?: string
  action_data?: Record<string, unknown>
  created_at?: string
}

interface Restaurant {
  id: string
  website_id: string
  total_orders: number
  completed_orders: number
  fulfillment_rate: number
  complaint_rate: number
  health_status: string
  websites?: { business_name?: string; subdomain?: string }
}

interface MonitorEvent {
  id: string
  event_type: string
  description: string
  severity: string
  created_at: string
  user_id?: string
}

type ActiveTab = 'overview' | 'disputes' | 'chats' | 'restaurants' | 'monitor'

export default function AdminPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [accessDenied, setAccessDenied] = useState(false)
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview')
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [disputes, setDisputes] = useState<Dispute[]>([])
  const [chats, setChats] = useState<Chat[]>([])
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [restaurants, setRestaurants] = useState<Restaurant[]>([])
  const [monitorEvents, setMonitorEvents] = useState<MonitorEvent[]>([])

  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    const token = getStoredToken()
    if (!token) {
      router.push('/login?redirect=/admin')
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
      router.push('/login?redirect=/admin')
      throw new Error('Session expired')
    }
    if (res.status === 403) {
      setAccessDenied(true)
      throw new Error('Admin access required')
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Request failed')
    }
    return res.json()
  }, [router])

  useEffect(() => {
    async function loadDashboard() {
      try {
        const data = await apiFetch('/api/v1/admin/dashboard')
        setStats(data)
      } catch (err) {
        console.error('Failed to load dashboard:', err)
      } finally {
        setLoading(false)
      }
    }
    loadDashboard()
  }, [apiFetch])

  useEffect(() => {
    async function loadTabData() {
      try {
        if (activeTab === 'disputes') {
          const data = await apiFetch('/api/v1/admin/disputes/escalated')
          setDisputes(data.disputes || [])
        } else if (activeTab === 'chats') {
          const data = await apiFetch('/api/v1/admin/chats/escalated')
          setChats(data.chats || [])
        } else if (activeTab === 'restaurants') {
          const data = await apiFetch('/api/v1/admin/restaurants')
          setRestaurants(data.restaurants || [])
        } else if (activeTab === 'monitor') {
          const data = await apiFetch('/api/v1/admin/monitor/events?limit=50')
          setMonitorEvents(data.events || [])
        }
      } catch (err) {
        console.error(`Failed to load ${activeTab}:`, err)
      }
    }
    if (!loading && !accessDenied) {
      loadTabData()
    }
  }, [activeTab, loading, accessDenied, apiFetch])

  const handleApproveDispute = async (disputeId: string, notes: string) => {
    await apiFetch(`/api/v1/admin/disputes/${disputeId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_type: 'credit', notes }),
    })
    setDisputes((prev) => prev.filter((d) => d.id !== disputeId))
  }

  const handleOverrideDispute = async (disputeId: string, resolution: string, notes: string, creditAmount?: number) => {
    await apiFetch(`/api/v1/admin/disputes/${disputeId}/override`, {
      method: 'POST',
      body: JSON.stringify({ resolution_type: resolution, notes, credit_amount: creditAmount }),
    })
    setDisputes((prev) => prev.filter((d) => d.id !== disputeId))
  }

  const handleRejectDispute = async (disputeId: string, notes: string) => {
    await apiFetch(`/api/v1/admin/disputes/${disputeId}/override`, {
      method: 'POST',
      body: JSON.stringify({ resolution_type: 'rejected', notes }),
    })
    setDisputes((prev) => prev.filter((d) => d.id !== disputeId))
  }

  const handleViewChat = async (chatId: string) => {
    setSelectedChatId(chatId)
    try {
      const data = await apiFetch(`/api/v1/admin/chats/${chatId}/messages`)
      setChatMessages(data.messages || [])
    } catch (err) {
      console.error('Failed to load chat:', err)
    }
  }

  const handleAdminRespond = async (chatId: string, message: string) => {
    await apiFetch(`/api/v1/admin/chats/${chatId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    })
    // Reload messages
    const data = await apiFetch(`/api/v1/admin/chats/${chatId}/messages`)
    setChatMessages(data.messages || [])
  }

  const handleSuspendRestaurant = async (websiteId: string) => {
    const reason = prompt('Sebab penggantungan:')
    if (!reason) return
    await apiFetch(`/api/v1/admin/restaurants/${websiteId}/suspend`, {
      method: 'POST',
      body: JSON.stringify({ notes: reason }),
    })
    const data = await apiFetch('/api/v1/admin/restaurants')
    setRestaurants(data.restaurants || [])
  }

  const handleUnsuspendRestaurant = async (websiteId: string) => {
    await apiFetch(`/api/v1/admin/restaurants/${websiteId}/unsuspend`, {
      method: 'POST',
      body: JSON.stringify({ notes: 'Unsuspended by admin' }),
    })
    const data = await apiFetch('/api/v1/admin/restaurants')
    setRestaurants(data.restaurants || [])
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

  if (accessDenied) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-2xl mb-2">🔒</p>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">Akses Ditolak</h2>
          <p className="text-sm text-gray-500 mb-4">Anda tidak mempunyai akses admin.</p>
          <Link href="/profil" className="text-sm text-blue-600 hover:underline">
            Kembali ke Dashboard
          </Link>
        </div>
      </div>
    )
  }

  const tabs: { key: ActiveTab; label: string }[] = [
    { key: 'overview', label: 'Gambaran' },
    { key: 'disputes', label: `Aduan (${stats?.escalated_disputes || 0})` },
    { key: 'chats', label: `Chat (${stats?.escalated_chats || 0})` },
    { key: 'restaurants', label: 'Restoran' },
    { key: 'monitor', label: `Monitor (${stats?.monitor_events_unacknowledged || 0})` },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-800">Admin Dashboard</h1>
            <p className="text-xs text-gray-500">BinaApp Platform Management</p>
          </div>
          <Link href="/profil" className="text-sm text-blue-600 hover:underline">
            Kembali ke Dashboard
          </Link>
        </div>

        {/* Tabs */}
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex gap-1 overflow-x-auto pb-0">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Overview */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              <AdminStatCard label="Jumlah Pengguna" value={stats.total_users} color="blue" />
              <AdminStatCard label="Langganan Aktif" value={stats.active_subscriptions} color="green" />
              <AdminStatCard label="Aduan Hari Ini" value={stats.total_disputes_today} color="yellow" />
              <AdminStatCard label="Kadar AI" value={`${stats.ai_resolution_rate}%`} color="purple" />
              <AdminStatCard label="Kredit Hari Ini" value={`RM${stats.total_credits_awarded_today}`} color="green" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <AdminStatCard
                label="Eskalasi"
                value={stats.escalated_disputes + stats.escalated_chats}
                color="red"
              />
              <AdminStatCard label="Chat Aktif" value={stats.active_support_chats} color="blue" />
              <AdminStatCard label="Web Tidak Sihat" value={stats.websites_unhealthy} color="yellow" />
              <AdminStatCard label="Monitor Belum Baca" value={stats.monitor_events_unacknowledged} color="gray" />
            </div>
          </div>
        )}

        {/* Escalated Disputes */}
        {activeTab === 'disputes' && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-700">Aduan Eskalasi</h2>
            {disputes.length === 0 ? (
              <p className="text-center py-12 text-gray-400">Tiada aduan eskalasi.</p>
            ) : (
              disputes.map((dispute) => (
                <EscalatedDisputeCard
                  key={dispute.id}
                  dispute={dispute}
                  onApprove={handleApproveDispute}
                  onOverride={handleOverrideDispute}
                  onReject={handleRejectDispute}
                />
              ))
            )}
          </div>
        )}

        {/* Escalated Chats */}
        {activeTab === 'chats' && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-700">Chat Eskalasi</h2>
            {selectedChatId ? (
              <div>
                <button
                  onClick={() => { setSelectedChatId(null); setChatMessages([]) }}
                  className="text-sm text-blue-600 hover:underline mb-3 inline-flex items-center gap-1"
                >
                  &larr; Kembali
                </button>
                <ChatViewer
                  chatId={selectedChatId}
                  messages={chatMessages}
                  chatStatus={chats.find((c) => c.id === selectedChatId)?.status}
                  onAdminRespond={handleAdminRespond}
                />
              </div>
            ) : (
              <>
                {chats.length === 0 ? (
                  <p className="text-center py-12 text-gray-400">Tiada chat eskalasi.</p>
                ) : (
                  chats.map((chat) => (
                    <div
                      key={chat.id}
                      onClick={() => handleViewChat(chat.id)}
                      className="border rounded-lg bg-white p-4 cursor-pointer hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-800">
                            {chat.title || `Chat #${chat.id.slice(0, 8)}`}
                          </p>
                          <p className="text-xs text-gray-400">
                            User: {chat.user_id?.slice(0, 8)}... | {chat.category || 'Umum'}
                          </p>
                        </div>
                        <span className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded-full">
                          Eskalasi
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </>
            )}
          </div>
        )}

        {/* Restaurants */}
        {activeTab === 'restaurants' && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-700">Kesihatan Restoran</h2>
            {restaurants.length === 0 ? (
              <p className="text-center py-12 text-gray-400">Tiada data restoran.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full bg-white border rounded-xl overflow-hidden">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left px-4 py-2 text-xs font-medium text-gray-500">Restoran</th>
                      <th className="text-center px-4 py-2 text-xs font-medium text-gray-500">Pesanan</th>
                      <th className="text-center px-4 py-2 text-xs font-medium text-gray-500">Pemenuhan</th>
                      <th className="text-center px-4 py-2 text-xs font-medium text-gray-500">Aduan</th>
                      <th className="text-center px-4 py-2 text-xs font-medium text-gray-500">Status</th>
                      <th className="text-center px-4 py-2 text-xs font-medium text-gray-500">Tindakan</th>
                    </tr>
                  </thead>
                  <tbody>
                    {restaurants.map((r) => (
                      <tr key={r.id} className="border-t">
                        <td className="px-4 py-3 text-sm text-gray-700">
                          {r.websites?.business_name || r.website_id.slice(0, 8)}
                        </td>
                        <td className="text-center px-4 py-3 text-sm">{r.total_orders}</td>
                        <td className="text-center px-4 py-3 text-sm">
                          <span className={r.fulfillment_rate < 70 ? 'text-red-600 font-medium' : 'text-green-600'}>
                            {r.fulfillment_rate}%
                          </span>
                        </td>
                        <td className="text-center px-4 py-3 text-sm">
                          <span className={r.complaint_rate > 30 ? 'text-red-600 font-medium' : ''}>
                            {r.complaint_rate}%
                          </span>
                        </td>
                        <td className="text-center px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            r.health_status === 'healthy' ? 'bg-green-100 text-green-700' :
                            r.health_status === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                            r.health_status === 'critical' ? 'bg-red-100 text-red-700' :
                            'bg-gray-200 text-gray-600'
                          }`}>
                            {r.health_status}
                          </span>
                        </td>
                        <td className="text-center px-4 py-3">
                          {r.health_status !== 'suspended' ? (
                            <button
                              onClick={() => handleSuspendRestaurant(r.website_id)}
                              className="text-xs text-red-600 hover:underline"
                            >
                              Gantung
                            </button>
                          ) : (
                            <button
                              onClick={() => handleUnsuspendRestaurant(r.website_id)}
                              className="text-xs text-green-600 hover:underline"
                            >
                              Aktifkan
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Monitor Events */}
        {activeTab === 'monitor' && (
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-gray-700">Suapan Monitor Platform</h2>
            {monitorEvents.length === 0 ? (
              <p className="text-center py-12 text-gray-400">Tiada peristiwa.</p>
            ) : (
              monitorEvents.map((event) => (
                <div key={event.id} className={`border rounded-lg p-3 ${
                  event.severity === 'critical' ? 'bg-red-50 border-red-200' :
                  event.severity === 'warning' ? 'bg-yellow-50 border-yellow-200' :
                  'bg-blue-50 border-blue-200'
                }`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                        event.severity === 'critical' ? 'bg-red-200 text-red-800' :
                        event.severity === 'warning' ? 'bg-yellow-200 text-yellow-800' :
                        'bg-blue-200 text-blue-800'
                      }`}>
                        {event.severity}
                      </span>
                      <span className="text-xs text-gray-500 ml-2">{event.event_type}</span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(event.created_at).toLocaleString('ms-MY')}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mt-1">{event.description}</p>
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  )
}

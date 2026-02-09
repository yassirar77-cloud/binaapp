'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface Notification {
  id: string
  title: string
  message: string
  notification_type: string
  priority: string
  is_read: boolean
  action_url: string | null
  created_at: string
}

const typeLabels: Record<string, string> = {
  sla_breach: 'SLA',
  referral: 'Rujukan',
  credit: 'Kredit',
  dispute: 'Pertikaian',
  order: 'Pesanan',
  website: 'Laman Web',
  penalty: 'Penalti',
  trust: 'Kepercayaan',
  system: 'Sistem',
  announcement: 'Pengumuman'
}

const priorityColors: Record<string, string> = {
  low: 'bg-gray-100 text-gray-600',
  normal: 'bg-blue-100 text-blue-600',
  high: 'bg-orange-100 text-orange-600',
  urgent: 'bg-red-100 text-red-600'
}

const typeColors: Record<string, string> = {
  sla_breach: 'bg-red-100 text-red-700',
  referral: 'bg-green-100 text-green-700',
  credit: 'bg-emerald-100 text-emerald-700',
  dispute: 'bg-yellow-100 text-yellow-700',
  order: 'bg-blue-100 text-blue-700',
  website: 'bg-purple-100 text-purple-700',
  penalty: 'bg-red-100 text-red-700',
  trust: 'bg-indigo-100 text-indigo-700',
  system: 'bg-gray-100 text-gray-700',
  announcement: 'bg-pink-100 text-pink-700'
}

export default function NotificationsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [filter, setFilter] = useState<string>('')
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    loadData()
  }, [filter])

  const loadData = async () => {
    try {
      const token = getStoredToken()
      if (!token) { router.push('/auth/login'); return }

      const headers = { 'Authorization': `Bearer ${token}` }
      const filterParam = filter ? `&type_filter=${filter}` : ''

      const [notifResp, countResp] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/notifications?limit=50${filterParam}`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/notifications/unread-count`, { headers })
      ])

      if (notifResp.ok) {
        const d = await notifResp.json()
        setNotifications(d.data || [])
      }
      if (countResp.ok) {
        const d = await countResp.json()
        setUnreadCount(d.data?.count || 0)
      }
    } catch (err) {
      console.error('Error loading notifications:', err)
    } finally {
      setLoading(false)
    }
  }

  const markRead = async (id: string) => {
    try {
      const token = getStoredToken()
      await fetch(`${API_BASE_URL}/api/v1/notifications/${id}/read`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: true } : n)
      )
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch (err) {
      console.error('Error marking read:', err)
    }
  }

  const markAllRead = async () => {
    try {
      const token = getStoredToken()
      await fetch(`${API_BASE_URL}/api/v1/notifications/read-all`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch (err) {
      console.error('Error marking all read:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <button onClick={() => router.push('/profile')} className="text-blue-600 text-sm mb-2 hover:underline">&larr; Kembali ke Profil</button>
            <h1 className="text-2xl font-bold text-gray-900">Pemberitahuan</h1>
            {unreadCount > 0 && (
              <p className="text-sm text-gray-600">{unreadCount} belum dibaca</p>
            )}
          </div>
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="text-blue-600 text-sm hover:underline"
            >
              Tandai semua dibaca
            </button>
          )}
        </div>

        {/* Type Filter */}
        <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
          <button
            onClick={() => setFilter('')}
            className={`px-3 py-1 rounded-full text-xs whitespace-nowrap ${!filter ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border'}`}
          >Semua</button>
          {Object.entries(typeLabels).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1 rounded-full text-xs whitespace-nowrap ${filter === key ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border'}`}
            >{label}</button>
          ))}
        </div>

        {/* Notification List */}
        <div className="bg-white rounded-lg shadow">
          {notifications.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              Tiada pemberitahuan
            </div>
          ) : (
            <div className="divide-y">
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => {
                    if (!notif.is_read) markRead(notif.id)
                    if (notif.action_url) router.push(notif.action_url)
                  }}
                  className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${!notif.is_read ? 'bg-blue-50/50' : ''}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-xs ${typeColors[notif.notification_type] || 'bg-gray-100 text-gray-600'}`}>
                          {typeLabels[notif.notification_type] || notif.notification_type}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-xs ${priorityColors[notif.priority] || ''}`}>
                          {notif.priority}
                        </span>
                        {!notif.is_read && (
                          <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                        )}
                      </div>
                      <h3 className={`font-medium ${!notif.is_read ? 'text-gray-900' : 'text-gray-700'}`}>{notif.title}</h3>
                      <p className="text-sm text-gray-600 mt-1">{notif.message}</p>
                      <p className="text-xs text-gray-400 mt-2">
                        {new Date(notif.created_at).toLocaleString('ms-MY')}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

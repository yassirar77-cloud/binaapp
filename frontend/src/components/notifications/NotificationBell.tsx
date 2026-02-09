'use client'

import { useState, useEffect, useRef } from 'react'
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

export default function NotificationBell() {
  const router = useRouter()
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Poll every 30 seconds
  useEffect(() => {
    fetchUnreadCount()
    const interval = setInterval(fetchUnreadCount, 30000)
    return () => clearInterval(interval)
  }, [])

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchUnreadCount = async () => {
    try {
      const token = getStoredToken()
      if (!token) return

      const response = await fetch(`${API_BASE_URL}/api/v1/notifications/unread-count`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const d = await response.json()
        setUnreadCount(d.data?.count || 0)
      }
    } catch {
      // Silent fail for polling
    }
  }

  const fetchRecent = async () => {
    try {
      const token = getStoredToken()
      if (!token) return

      const response = await fetch(`${API_BASE_URL}/api/v1/notifications?limit=5`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const d = await response.json()
        setNotifications(d.data || [])
      }
    } catch {
      // Silent fail
    }
  }

  const toggleDropdown = () => {
    if (!showDropdown) {
      fetchRecent()
    }
    setShowDropdown(!showDropdown)
  }

  const markRead = async (id: string) => {
    try {
      const token = getStoredToken()
      await fetch(`${API_BASE_URL}/api/v1/notifications/${id}/read`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch {
      // Silent fail
    }
  }

  const timeAgo = (dateStr: string) => {
    const now = new Date()
    const date = new Date(dateStr)
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (seconds < 60) return 'baru sahaja'
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minit lalu`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} jam lalu`
    return `${Math.floor(seconds / 86400)} hari lalu`
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={toggleDropdown}
        className="relative p-2 text-gray-600 hover:text-gray-800 transition-colors"
        aria-label="Pemberitahuan"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>

        {/* Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border z-50 overflow-hidden">
          <div className="p-3 border-b flex items-center justify-between bg-gray-50">
            <span className="font-semibold text-sm">Pemberitahuan</span>
            {unreadCount > 0 && (
              <span className="bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded-full">
                {unreadCount} baharu
              </span>
            )}
          </div>

          {notifications.length === 0 ? (
            <div className="p-6 text-center text-gray-500 text-sm">
              Tiada pemberitahuan
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => {
                    if (!notif.is_read) markRead(notif.id)
                    if (notif.action_url) {
                      router.push(notif.action_url)
                      setShowDropdown(false)
                    }
                  }}
                  className={`p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 transition-colors ${!notif.is_read ? 'bg-blue-50/50' : ''}`}
                >
                  <div className="flex items-start gap-2">
                    {!notif.is_read && <span className="w-2 h-2 bg-blue-500 rounded-full mt-1.5 flex-shrink-0"></span>}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1 mb-0.5">
                        <span className={`px-1.5 py-0.5 rounded text-xs ${typeColors[notif.notification_type] || 'bg-gray-100'}`}>
                          {notif.notification_type}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-900 truncate">{notif.title}</p>
                      <p className="text-xs text-gray-500 truncate">{notif.message}</p>
                      <p className="text-xs text-gray-400 mt-1">{timeAgo(notif.created_at)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="p-2 border-t bg-gray-50">
            <button
              onClick={() => { router.push('/notifications'); setShowDropdown(false) }}
              className="w-full text-center text-blue-600 text-sm py-1 hover:underline"
            >
              Lihat semua pemberitahuan
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

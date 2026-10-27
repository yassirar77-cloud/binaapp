'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import toast from 'react-hot-toast'
import { Card, LoadingSpinner, EmptyState } from '@/components/ui/Card'
import { formatTime, timeAgo } from '@/lib/utils'
import { apiFetch } from '@/lib/api-fetch'

type ActivityItem = {
  id: string
  type: 'user' | 'website' | 'error' | 'payment' | 'generation'
  message: string
  detail: string
  created_at: string
  severity?: 'info' | 'success' | 'warning' | 'error'
}

const typeConfig: Record<string, { icon: string; color: string }> = {
  user: { icon: '\u{1F7E2}', color: 'text-green-400' },
  website: { icon: '\u{1F310}', color: 'text-blue-400' },
  error: { icon: '\u{274C}', color: 'text-red-400' },
  payment: { icon: '\u{1F4B0}', color: 'text-yellow-400' },
  generation: { icon: '\u{1F310}', color: 'text-blue-400' },
}

const POLL_MS = 30000

export function ActivityPage() {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [isLive, setIsLive] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  const fetchActivities = useCallback(async () => {
    try {
      const res = await apiFetch('/api/activity')
      if (!res.ok) throw new Error(`Activity request failed (${res.status})`)
      const data = await res.json()
      setActivities(data.activities ?? [])
    } catch (err) {
      console.error('Failed to fetch activities:', err)
      toast.error('Failed to load activity')
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load
  useEffect(() => {
    fetchActivities()
  }, [fetchActivities])

  // Poll while LIVE is on; the LIVE button pauses/resumes this interval.
  // (The previous Supabase Realtime channel never delivered events: the anon
  // client has no session and the tables are RLS-protected / not published.)
  useEffect(() => {
    if (!isLive) return
    fetchActivities()
    const interval = setInterval(fetchActivities, POLL_MS)
    return () => clearInterval(interval)
  }, [isLive, fetchActivities])

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4 px-4 py-4">
      {/* Live indicator / pause toggle */}
      <div className="flex items-center justify-center gap-2">
        <button
          onClick={() => setIsLive(!isLive)}
          title={isLive ? 'Pause auto-refresh' : 'Resume auto-refresh'}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            isLive
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : 'bg-gray-800 text-gray-500 border border-gray-700'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-red-500 animate-pulse' : 'bg-gray-600'}`} />
          {isLive ? 'LIVE' : 'PAUSED'}
        </button>
      </div>

      {activities.length === 0 ? (
        <EmptyState message="No recent activity" />
      ) : (
        <div className="space-y-2">
          {activities.map(activity => {
            const cfg = typeConfig[activity.type] || typeConfig.generation
            return (
              <Card key={activity.id} className="py-3">
                <div className="flex items-start gap-3">
                  <span className="text-sm mt-0.5">{cfg.icon}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">
                        {formatTime(activity.created_at)}
                      </span>
                      <span className="text-xs text-gray-600">&mdash;</span>
                      <span className={`text-xs font-medium ${cfg.color}`}>
                        {activity.message}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5 break-all">
                      {activity.detail}
                    </p>
                  </div>
                  <span className="text-[10px] text-gray-600 whitespace-nowrap">
                    {timeAgo(activity.created_at)}
                  </span>
                </div>
              </Card>
            )
          })}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

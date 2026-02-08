'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, LoadingSpinner, EmptyState } from '@/components/ui/Card'
import { formatTime, timeAgo } from '@/lib/utils'
import { supabase } from '@/lib/supabase'

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

export function ActivityPage() {
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [isLive, setIsLive] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  const fetchActivities = useCallback(async () => {
    try {
      const res = await fetch('/api/activity')
      const data = await res.json()
      setActivities(data.activities ?? [])
    } catch (err) {
      console.error('Failed to fetch activities:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchActivities()

    // Set up Supabase Realtime subscriptions
    const channel = supabase
      .channel('admin-activity')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'profiles' }, (payload) => {
        const newActivity: ActivityItem = {
          id: `user-${payload.new.id}-${Date.now()}`,
          type: 'user',
          message: 'New user registered',
          detail: payload.new.full_name || 'Unknown user',
          created_at: payload.new.created_at || new Date().toISOString(),
          severity: 'success',
        }
        setActivities(prev => [newActivity, ...prev].slice(0, 50))
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'websites' }, (payload) => {
        if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
          const w = payload.new
          let message = 'Website updated'
          let severity: ActivityItem['severity'] = 'info'
          if (w.status === 'published') {
            message = 'Website published'
            severity = 'success'
          } else if (w.status === 'generating') {
            message = 'Website generating...'
            severity = 'info'
          } else if (w.status === 'failed') {
            message = 'Website generation failed'
            severity = 'error'
          }
          const newActivity: ActivityItem = {
            id: `web-${w.id}-${Date.now()}`,
            type: w.status === 'failed' ? 'error' : 'website',
            message,
            detail: `${w.subdomain || w.business_name || 'Unknown'}.binaapp.my`,
            created_at: w.updated_at || w.created_at || new Date().toISOString(),
            severity,
          }
          setActivities(prev => [newActivity, ...prev].slice(0, 50))
        }
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'generation_jobs' }, (payload) => {
        const j = payload.new
        if (j.status === 'failed') {
          const newActivity: ActivityItem = {
            id: `job-${j.id}-${Date.now()}`,
            type: 'error',
            message: 'Generation failed',
            detail: `${j.error?.substring(0, 80) || 'Unknown error'} (Job: ${j.job_id?.substring(0, 8)})`,
            created_at: j.created_at || new Date().toISOString(),
            severity: 'error',
          }
          setActivities(prev => [newActivity, ...prev].slice(0, 50))
        }
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'transactions' }, (payload) => {
        const t = payload.new
        const newActivity: ActivityItem = {
          id: `pay-${t.transaction_id}-${Date.now()}`,
          type: 'payment',
          message: t.payment_status === 'success' ? 'Payment received' : 'Payment pending',
          detail: `RM ${t.amount} - ${t.item_description || 'Transaction'}`,
          created_at: t.created_at || new Date().toISOString(),
          severity: t.payment_status === 'success' ? 'success' : 'info',
        }
        setActivities(prev => [newActivity, ...prev].slice(0, 50))
      })
      .subscribe()

    // Also poll every 30 seconds as backup
    const interval = setInterval(fetchActivities, 30000)

    return () => {
      supabase.removeChannel(channel)
      clearInterval(interval)
    }
  }, [fetchActivities])

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4 px-4 py-4">
      {/* Live indicator */}
      <div className="flex items-center justify-center gap-2">
        <button
          onClick={() => setIsLive(!isLive)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            isLive
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : 'bg-gray-800 text-gray-500 border border-gray-700'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-red-500 animate-pulse' : 'bg-gray-600'}`} />
          LIVE
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

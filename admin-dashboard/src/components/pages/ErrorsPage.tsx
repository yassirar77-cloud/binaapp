'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, Badge, LoadingSpinner, EmptyState } from '@/components/ui/Card'
import { formatDateTime, timeAgo } from '@/lib/utils'

type ErrorItem = {
  id: string
  job_id: string
  error: string
  user_id: string
  user_name: string
  created_at: string
  severity: 'critical' | 'error' | 'warning' | 'info'
  error_type: string
}

type ErrorSummary = {
  total: number
  deepseek: number
  qwen: number
  stability: number
}

const severityConfig: Record<string, { color: 'red' | 'yellow' | 'green' | 'blue'; icon: string; label: string }> = {
  critical: { color: 'red', icon: '\u{1F534}', label: 'CRITICAL' },
  error: { color: 'red', icon: '\u{1F534}', label: 'ERROR' },
  warning: { color: 'yellow', icon: '\u{1F7E1}', label: 'WARNING' },
  info: { color: 'green', icon: '\u{1F7E2}', label: 'INFO' },
}

export function ErrorsPage() {
  const [errors, setErrors] = useState<ErrorItem[]>([])
  const [summary, setSummary] = useState<ErrorSummary>({ total: 0, deepseek: 0, qwen: 0, stability: 0 })
  const [loading, setLoading] = useState(true)
  const [expandedError, setExpandedError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/errors')
      const data = await res.json()
      setErrors(data.errors ?? [])
      setSummary(data.todaySummary ?? { total: 0, deepseek: 0, qwen: 0, stability: 0 })
    } catch (err) {
      console.error('Failed to fetch errors:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 15000) // Refresh every 15s
    return () => clearInterval(interval)
  }, [fetchData])

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white">Errors & Bugs</h2>

      {/* Today's Error Summary */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Errors Today: <span className={summary.total > 0 ? 'text-red-400' : 'text-green-400'}>{summary.total}</span>
        </h3>
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">DeepSeek API failures</span>
            <span className={summary.deepseek > 0 ? 'text-red-400 font-semibold' : 'text-gray-500'}>{summary.deepseek}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Qwen API failures</span>
            <span className={summary.qwen > 0 ? 'text-yellow-400 font-semibold' : 'text-gray-500'}>{summary.qwen}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Stability AI failures</span>
            <span className={summary.stability > 0 ? 'text-yellow-400 font-semibold' : 'text-gray-500'}>{summary.stability}</span>
          </div>
        </div>
        {summary.total === 0 && (
          <p className="text-xs text-green-400 mt-3">All systems operational</p>
        )}
      </Card>

      {/* Error Log */}
      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Error Log</h3>
        {errors.length === 0 ? (
          <EmptyState message="No errors recorded" />
        ) : (
          <div className="space-y-2">
            {errors.map(err => {
              const cfg = severityConfig[err.severity] || severityConfig.error
              return (
                <Card key={err.id}>
                  <button
                    className="w-full text-left"
                    onClick={() => setExpandedError(expandedError === err.id ? null : err.id)}
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-sm mt-0.5">{cfg.icon}</span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Badge color={cfg.color}>{cfg.label}</Badge>
                          <span className="text-xs text-gray-500 capitalize">{err.error_type}</span>
                        </div>
                        <p className="text-xs text-gray-300 mt-1 line-clamp-2">
                          {err.error || 'Unknown error'}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5 text-[10px] text-gray-500">
                          <span>{timeAgo(err.created_at)}</span>
                          <span>&#183;</span>
                          <span>User: {err.user_name}</span>
                        </div>
                      </div>
                    </div>
                  </button>

                  {expandedError === err.id && (
                    <div className="mt-3 pt-3 border-t border-gray-800 space-y-2">
                      <div className="text-xs space-y-1">
                        <div>
                          <span className="text-gray-500">Job ID: </span>
                          <span className="text-gray-300 font-mono">{err.job_id || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">User ID: </span>
                          <span className="text-gray-300 font-mono text-[10px] break-all">{err.user_id}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Time: </span>
                          <span className="text-gray-300">{formatDateTime(err.created_at)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Full Error: </span>
                          <p className="text-red-400 bg-red-500/10 rounded-lg p-2 mt-1 break-all">
                            {err.error || 'No error message'}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

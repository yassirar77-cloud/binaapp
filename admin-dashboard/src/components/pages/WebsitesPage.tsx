'use client'

import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Card, SearchInput, FilterChip, Badge, LoadingSpinner, EmptyState } from '@/components/ui/Card'
import { formatDate } from '@/lib/utils'
import { apiFetch } from '@/lib/api-fetch'

type Website = {
  id: string
  business_name: string
  business_type: string
  subdomain: string
  status: string
  language: string
  published_at: string | null
  created_at: string
  error_message: string | null
  owner_name: string
}

type Counts = {
  total: number
  published: number
  draft: number
  failed: number
}

const statusConfig: Record<string, { color: 'green' | 'yellow' | 'red' | 'blue' | 'gray'; label: string }> = {
  published: { color: 'green', label: 'Published' },
  draft: { color: 'yellow', label: 'Draft' },
  generating: { color: 'blue', label: 'Generating' },
  failed: { color: 'red', label: 'Failed' },
}

export function WebsitesPage() {
  const [websites, setWebsites] = useState<Website[]>([])
  const [counts, setCounts] = useState<Counts>({ total: 0, published: 0, draft: 0, failed: 0 })
  const [filteredTotal, setFilteredTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const fetchData = useCallback(async (pageToLoad: number) => {
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (statusFilter) params.set('status', statusFilter)
      if (pageToLoad > 1) params.set('page', String(pageToLoad))
      const res = await apiFetch(`/api/websites?${params}`)
      if (!res.ok) throw new Error(`Websites request failed (${res.status})`)
      const data = await res.json()
      const rows: Website[] = data.websites ?? []
      setWebsites(prev => (pageToLoad > 1 ? [...prev, ...rows] : rows))
      setFilteredTotal(data.total ?? 0)
      setCounts(data.counts ?? { total: 0, published: 0, draft: 0, failed: 0 })
    } catch (err) {
      console.error('Failed to fetch websites:', err)
      toast.error('Failed to load websites')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [search, statusFilter])

  // Search / filter changes reset to page 1 (debounced)
  useEffect(() => {
    setLoading(true)
    setPage(1)
    const timeout = setTimeout(() => fetchData(1), 300)
    return () => clearTimeout(timeout)
  }, [fetchData])

  const hasMore = websites.length < filteredTotal

  const loadMore = () => {
    const next = page + 1
    setPage(next)
    setLoadingMore(true)
    fetchData(next)
  }

  const successRate = counts.total > 0
    ? (((counts.total - counts.failed) / counts.total) * 100).toFixed(1)
    : '0'

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-white">Websites</h2>

      {/* Top Stats */}
      <Card>
        <div className="grid grid-cols-2 gap-3 text-center">
          <div>
            <p className="text-2xl font-bold text-white">{counts.total}</p>
            <p className="text-xs text-gray-400">Total Generated</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-400">{counts.published}</p>
            <p className="text-xs text-gray-400">Published</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-yellow-400">{counts.draft}</p>
            <p className="text-xs text-gray-400">Draft</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-red-400">{counts.failed}</p>
            <p className="text-xs text-gray-400">Failed</p>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-gray-800 text-center">
          <p className="text-sm text-gray-400">
            Success Rate: <span className="text-white font-semibold">{successRate}%</span>
          </p>
        </div>
      </Card>

      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Search by name or subdomain..."
      />

      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        <FilterChip label="All" active={statusFilter === ''} onClick={() => setStatusFilter('')} />
        <FilterChip label="Published" active={statusFilter === 'published'} onClick={() => setStatusFilter('published')} />
        <FilterChip label="Draft" active={statusFilter === 'draft'} onClick={() => setStatusFilter('draft')} />
        <FilterChip label="Failed" active={statusFilter === 'failed'} onClick={() => setStatusFilter('failed')} />
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : websites.length === 0 ? (
        <EmptyState message="No websites found" />
      ) : (
        <div className="space-y-2">
          {websites.map(w => {
            const cfg = statusConfig[w.status] || { color: 'gray' as const, label: w.status }
            return (
              <Card key={w.id}>
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-white truncate">
                      {w.subdomain ? `${w.subdomain}.binaapp.my` : w.business_name}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {w.business_name}
                    </p>
                  </div>
                  <Badge color={cfg.color}>{cfg.label}</Badge>
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <span>Created {formatDate(w.created_at)}</span>
                  {w.business_type && (
                    <>
                      <span>&#183;</span>
                      <span className="capitalize">{w.business_type}</span>
                    </>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Owner: {w.owner_name}
                </p>
                {w.status === 'published' && w.subdomain && (
                  <a
                    href={`https://${w.subdomain}.binaapp.my`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 mt-2 text-xs text-brand-orange hover:text-brand-orange-light"
                  >
                    Visit site &#8594;
                  </a>
                )}
                {w.error_message && (
                  <p className="mt-2 text-xs text-red-400 bg-red-500/10 rounded-lg p-2">
                    {w.error_message}
                  </p>
                )}
              </Card>
            )
          })}

          {hasMore && (
            <button
              onClick={loadMore}
              disabled={loadingMore}
              className="w-full bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-300 text-sm font-medium py-3 rounded-xl transition-colors disabled:opacity-50"
            >
              {loadingMore ? 'Loading...' : `Load more (${websites.length} of ${filteredTotal})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

'use client'

import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Card, SearchInput, FilterChip, Badge, LoadingSpinner, EmptyState } from '@/components/ui/Card'
import { formatDate } from '@/lib/utils'
import { apiFetch } from '@/lib/api-fetch'

type User = {
  id: string
  full_name: string
  business_name: string | null
  phone: string | null
  created_at: string
  plan: string
  status: string
  website_count: number
}

const planLabels: Record<string, string> = {
  free: 'Free',
  starter: 'Starter RM5',
  basic: 'Basic RM29',
  pro: 'Pro RM49',
  enterprise: 'Enterprise',
}

const planColors: Record<string, 'gray' | 'green' | 'blue' | 'orange'> = {
  free: 'gray',
  starter: 'green',
  basic: 'blue',
  pro: 'orange',
  enterprise: 'orange',
}

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [search, setSearch] = useState('')
  const [planFilter, setPlanFilter] = useState('')
  const [page, setPage] = useState(1)
  const [expandedUser, setExpandedUser] = useState<string | null>(null)

  const fetchUsers = useCallback(async (pageToLoad: number) => {
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (planFilter) params.set('plan', planFilter)
      if (pageToLoad > 1) params.set('page', String(pageToLoad))
      const res = await apiFetch(`/api/users?${params}`)
      if (!res.ok) throw new Error(`Users request failed (${res.status})`)
      const data = await res.json()
      const rows: User[] = data.users ?? []
      setUsers(prev => (pageToLoad > 1 ? [...prev, ...rows] : rows))
      setTotal(data.total ?? 0)
    } catch (err) {
      console.error('Failed to fetch users:', err)
      toast.error('Failed to load users')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [search, planFilter])

  // Search / filter changes reset to page 1 (debounced)
  useEffect(() => {
    setLoading(true)
    setPage(1)
    const timeout = setTimeout(() => fetchUsers(1), 300) // Debounce search
    return () => clearTimeout(timeout)
  }, [fetchUsers])

  const hasMore = users.length < total

  const loadMore = () => {
    const next = page + 1
    setPage(next)
    setLoadingMore(true)
    fetchUsers(next)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Users</h2>
        <span className="text-sm text-gray-400">{total} pengguna berdaftar</span>
      </div>

      <SearchInput
        value={search}
        onChange={setSearch}
        placeholder="Search users..."
      />

      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        <FilterChip label="All" active={planFilter === ''} onClick={() => setPlanFilter('')} />
        <FilterChip label="Starter" active={planFilter === 'starter'} onClick={() => setPlanFilter('starter')} />
        <FilterChip label="Basic" active={planFilter === 'basic'} onClick={() => setPlanFilter('basic')} />
        <FilterChip label="Pro" active={planFilter === 'pro'} onClick={() => setPlanFilter('pro')} />
        <FilterChip label="Free" active={planFilter === 'free'} onClick={() => setPlanFilter('free')} />
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : users.length === 0 ? (
        <EmptyState message="No users found" />
      ) : (
        <div className="space-y-2">
          {users.map(user => (
            <Card
              key={user.id}
              className="cursor-pointer active:bg-gray-800 transition-colors"
            >
              <button
                className="w-full text-left"
                onClick={() => setExpandedUser(expandedUser === user.id ? null : user.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-white truncate">
                      {user.full_name}
                    </p>
                    {user.business_name && (
                      <p className="text-xs text-gray-500 truncate">{user.business_name}</p>
                    )}
                  </div>
                  <Badge color={user.status === 'active' ? 'green' : 'gray'}>
                    {user.status === 'active' ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  <span>Joined {formatDate(user.created_at)}</span>
                  <span>&#183;</span>
                  <Badge color={planColors[user.plan] || 'gray'}>
                    {planLabels[user.plan] || user.plan}
                  </Badge>
                  <span>&#183;</span>
                  <span>{user.website_count} site{user.website_count !== 1 ? 's' : ''}</span>
                </div>
              </button>

              {expandedUser === user.id && (
                <div className="mt-3 pt-3 border-t border-gray-800 space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-gray-500">User ID</p>
                      <p className="text-gray-300 font-mono text-[10px] break-all">{user.id}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Phone</p>
                      <p className="text-gray-300">{user.phone || 'Not set'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Plan</p>
                      <p className="text-gray-300">{planLabels[user.plan] || user.plan}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Websites</p>
                      <p className="text-gray-300">{user.website_count}</p>
                    </div>
                  </div>
                </div>
              )}
            </Card>
          ))}

          {hasMore && (
            <button
              onClick={loadMore}
              disabled={loadingMore}
              className="w-full bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-300 text-sm font-medium py-3 rounded-xl transition-colors disabled:opacity-50"
            >
              {loadingMore ? 'Loading...' : `Load more (${users.length} of ${total})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

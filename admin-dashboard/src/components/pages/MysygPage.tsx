'use client'

import { useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import { Card, SearchInput, FilterChip, Badge, LoadingSpinner, EmptyState } from '@/components/ui/Card'
import { formatCurrency, formatDateTime, timeAgo } from '@/lib/utils'
import { authHeaders } from '@/lib/require-founder'

type Wish = {
  id: string
  slug: string
  url: string
  status: string
  occasion: string
  package: string
  video_seconds: number | null
  amount: number
  sender_name: string
  recipient_name: string
  message: string
  photo_urls: string[]
  video_url: string | null
  poster_url: string | null
  video_direction: string | null
  video_error: string | null
  video_attempts: number
  payer_email: string
  payer_phone: string
  bill_code: string | null
  paid_at: string | null
  created_at: string
  unlock_at: string | null
  opened_at: string | null
  open_count: number
  view_count: number
  reaction: string | null
  reply_text: string | null
  replied_at: string | null
  since: { kind: string; date: string } | null
  secret_question: string | null
  hearts: number
}

type Summary = {
  revenue: { today: number; week: number; month: number; allTime: number }
  counts: {
    paid: number; free: number; ready: number; making: number; failed: number
    unpaid: number; cancelled: number; opened: number; replied: number
    senders: number; repeatSenders: number; hearts: number
  }
  byPackage: Record<string, { count: number; amount: number }>
  byOccasion: Record<string, number>
}

const STATUS: Record<string, { color: 'green' | 'yellow' | 'red' | 'blue' | 'gray'; label: string }> = {
  ready: { color: 'green', label: 'Ready' },
  paid: { color: 'blue', label: 'Paid · queued' },
  generating: { color: 'blue', label: 'Making video' },
  storing: { color: 'blue', label: 'Saving video' },
  video_failed: { color: 'red', label: 'Video failed' },
  awaiting_payment: { color: 'yellow', label: 'Unpaid' },
  cancelled: { color: 'gray', label: 'Cancelled' },
}

const OCCASIONS: Record<string, string> = {
  birthday: '🎂 Hari Jadi', anniversary: '💍 Ulang Tahun', love: '💖 Sayang', raya: '🌙 Raya',
  sorry: '🌷 Maaf', thanks: '🌻 Terima Kasih', congrats: '🎉 Tahniah', parents: '🤍 Mak & Ayah',
  graduation: '🎓 Graduasi', miss: '💌 Rindu', getwell: '🌼 Cepat Sembuh',
}

const PACKAGES: Record<string, string> = { ringkas: 'Ringkas', manis: 'Manis', sinematik: 'Sinematik' }

const FILTERS = [
  { id: '', label: 'All' },
  { id: 'paid', label: 'Paid' },
  { id: 'ready', label: 'Ready' },
  { id: 'making', label: 'Making' },
  { id: 'video_failed', label: 'Failed' },
  { id: 'awaiting_payment', label: 'Unpaid' },
]

function Stat({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-xs text-gray-400">{label}</p>
      {sub && <p className="text-[11px] text-gray-500 mt-0.5">{sub}</p>}
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-gray-800/70 last:border-0">
      <span className="text-xs text-gray-500 shrink-0">{label}</span>
      <span className="text-xs text-gray-200 text-right break-all">{children}</span>
    </div>
  )
}

function WishDetail({ w }: { w: Wish }) {
  return (
    <div className="mt-3 pt-3 border-t border-gray-800 space-y-3">
      <div className="flex flex-wrap gap-2">
        <a href={w.url} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1.5 rounded-lg bg-brand-orange px-3 py-2 text-xs font-semibold text-white">
          Open gift page ↗
        </a>
        {w.video_url && (
          <a href={w.video_url} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-1.5 rounded-lg border border-gray-700 px-3 py-2 text-xs font-semibold text-gray-200">
            Watch video ↗
          </a>
        )}
        <a href={`mailto:${w.payer_email}`}
           className="inline-flex items-center gap-1.5 rounded-lg border border-gray-700 px-3 py-2 text-xs font-semibold text-gray-200">
          Email sender
        </a>
        <a href={`https://wa.me/6${w.payer_phone}`} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1.5 rounded-lg border border-gray-700 px-3 py-2 text-xs font-semibold text-gray-200">
          WhatsApp sender
        </a>
      </div>

      {(w.poster_url || w.photo_urls.length > 0) && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {w.video_url ? (
            <video src={w.video_url} poster={w.poster_url || undefined} controls playsInline preload="none"
                   className="h-40 rounded-lg bg-black shrink-0" />
          ) : null}
          {w.photo_urls.map((u, i) => (
            <a key={i} href={u} target="_blank" rel="noopener noreferrer" className="shrink-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={u} alt={`Photo ${i + 1}`} loading="lazy" className="h-40 w-32 object-cover rounded-lg bg-gray-800" />
            </a>
          ))}
        </div>
      )}

      <div className="rounded-xl bg-gray-900/70 p-3">
        <p className="text-[11px] uppercase tracking-wider text-gray-500 mb-1">Message</p>
        <p className="text-sm text-gray-200 whitespace-pre-line break-words">{w.message}</p>
      </div>

      {w.reply_text || w.reaction ? (
        <div className="rounded-xl bg-pink-500/10 border border-pink-500/20 p-3">
          <p className="text-[11px] uppercase tracking-wider text-pink-300 mb-1">Reply from {w.recipient_name}</p>
          <p className="text-sm text-gray-100">{w.reaction} {w.reply_text}</p>
        </div>
      ) : null}

      <div>
        <Row label="Sender email">{w.payer_email}</Row>
        <Row label="Sender phone">{w.payer_phone}</Row>
        <Row label="Package">{PACKAGES[w.package] || w.package}{w.video_seconds ? ` · ${w.video_seconds}s` : ''}</Row>
        <Row label="Paid">{w.amount > 0 ? formatCurrency(w.amount) : 'Free (test email)'}{w.paid_at ? ` · ${formatDateTime(w.paid_at)}` : ''}</Row>
        {w.bill_code && <Row label="ToyyibPay bill">{w.bill_code}</Row>}
        <Row label="Created">{formatDateTime(w.created_at)}</Row>
        <Row label="Page views">{w.view_count}</Row>
        <Row label="Gift opened">{w.opened_at ? `${formatDateTime(w.opened_at)} · ${w.open_count}×` : 'Not yet'}</Row>
        {w.hearts > 0 && <Row label="Hearts sent back">💗 {w.hearts}</Row>}
        {w.unlock_at && <Row label="Sealed until">{formatDateTime(w.unlock_at)}</Row>}
        {w.secret_question && <Row label="Secret question">{w.secret_question}</Row>}
        {w.since && <Row label="Counter">{w.since.kind} since {w.since.date}</Row>}
        {w.video_direction && <Row label="Video direction">{w.video_direction}</Row>}
        {w.video_error && <Row label="Video error">{w.video_error} ({w.video_attempts} attempts)</Row>}
      </div>
    </div>
  )
}

export function MysygPage() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [wishes, setWishes] = useState<Wish[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('paid')
  const [open, setOpen] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (filter) params.set('status', filter)
      const res = await fetch(`/api/wishes?${params}`, { headers: authHeaders() })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'Failed to load mysyg wishes')
        return
      }
      setError('')
      setSummary(data.summary)
      setWishes(data.wishes ?? [])
      setTotal(data.total ?? 0)
    } catch (err) {
      console.error('Failed to fetch wishes:', err)
      toast.error('Failed to load mysyg wishes')
    } finally {
      setLoading(false)
    }
  }, [search, filter])

  useEffect(() => {
    setLoading(true)
    const t = setTimeout(fetchData, 300)
    return () => clearTimeout(t)
  }, [fetchData])

  if (loading && !summary) return <LoadingSpinner />
  if (error) return <EmptyState message={error} />
  if (!summary) return <EmptyState message="Failed to load mysyg wishes" />

  const c = summary.counts
  const openRate = c.paid ? Math.round((c.opened / c.paid) * 100) : 0
  const occasions = Object.entries(summary.byOccasion).sort((a, b) => b[1] - a[1])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">mysyg wishes</h2>
        <a href="https://buat.mysyg.com" target="_blank" rel="noopener noreferrer" className="text-xs text-brand-orange">
          buat.mysyg.com ↗
        </a>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Total paid</h3>
        <div className="space-y-3">
          <div className="flex justify-between"><span className="text-sm text-gray-400">Today</span><span className="text-sm font-semibold text-white">{formatCurrency(summary.revenue.today)}</span></div>
          <div className="flex justify-between"><span className="text-sm text-gray-400">This Week</span><span className="text-sm font-semibold text-white">{formatCurrency(summary.revenue.week)}</span></div>
          <div className="flex justify-between"><span className="text-sm text-gray-400">This Month</span><span className="text-sm font-semibold text-white">{formatCurrency(summary.revenue.month)}</span></div>
          <div className="flex justify-between border-t border-gray-800 pt-3"><span className="text-sm text-gray-400">All Time</span><span className="text-lg font-bold text-brand-orange">{formatCurrency(summary.revenue.allTime)}</span></div>
        </div>
      </Card>

      <Card>
        <div className="grid grid-cols-3 gap-3 text-center">
          <Stat label="Paid gifts" value={c.paid} sub={c.free ? `${c.free} free` : undefined} />
          <Stat label="Customers" value={c.senders} sub={c.repeatSenders ? `${c.repeatSenders} repeat` : undefined} />
          <Stat label="Opened" value={`${openRate}%`} sub={`${c.opened} of ${c.paid}`} />
          <Stat label="Ready" value={c.ready} />
          <Stat label="Making" value={c.making} />
          <Stat label="Failed" value={c.failed} />
          <Stat label="Replied" value={c.replied} />
          <Stat label="Hearts" value={c.hearts} />
          <Stat label="Unpaid" value={c.unpaid} sub="abandoned at pay" />
        </div>
      </Card>

      {Object.keys(summary.byPackage).length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">By package</h3>
          <div className="space-y-2">
            {Object.entries(summary.byPackage).map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm">
                <span className="text-gray-400">{PACKAGES[k] || k} · {v.count}</span>
                <span className="font-semibold text-white">{formatCurrency(v.amount)}</span>
              </div>
            ))}
          </div>
          {occasions.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-gray-300 mt-5 mb-3">By occasion</h3>
              <div className="flex flex-wrap gap-2">
                {occasions.map(([k, n]) => (
                  <span key={k} className="text-xs rounded-lg bg-gray-800 px-2.5 py-1.5 text-gray-200">{OCCASIONS[k] || k} · {n}</span>
                ))}
              </div>
            </>
          )}
        </Card>
      )}

      <SearchInput value={search} onChange={setSearch} placeholder="Search link, name, email, phone, bill…" />
      <div className="flex gap-2 overflow-x-auto pb-1">
        {FILTERS.map(f => (
          <FilterChip key={f.id} label={f.label} active={filter === f.id} onClick={() => setFilter(f.id)} />
        ))}
      </div>

      <p className="text-xs text-gray-500">{total} {total === 1 ? 'wish' : 'wishes'}{total > wishes.length ? ` (showing ${wishes.length})` : ''}</p>

      {wishes.length === 0 ? (
        <EmptyState message="No wishes here yet" />
      ) : (
        <div className="space-y-2">
          {wishes.map(w => {
            const s = STATUS[w.status] || { color: 'gray' as const, label: w.status }
            const isOpen = open === w.id
            return (
              <Card key={w.id} padding="sm">
                <button type="button" className="w-full text-left" onClick={() => setOpen(isOpen ? null : w.id)}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-white truncate">
                        {w.sender_name} → {w.recipient_name}
                      </p>
                      <p className="text-xs text-brand-orange truncate">{w.slug}.mysyg.com</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {OCCASIONS[w.occasion] || w.occasion} · {PACKAGES[w.package] || w.package} · {timeAgo(w.paid_at || w.created_at)}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{w.payer_email} · {w.payer_phone}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1.5 shrink-0">
                      <span className="text-sm font-bold text-white">{w.amount > 0 ? formatCurrency(w.amount) : 'Free'}</span>
                      <Badge color={s.color}>{s.label}</Badge>
                      <span className="text-[11px] text-gray-500">
                        {w.opened_at ? '🎁 opened' : 'not opened'}{w.reaction ? ` ${w.reaction}` : ''}{w.hearts ? ` 💗${w.hearts}` : ''}
                      </span>
                    </div>
                  </div>
                </button>
                {isOpen && <WishDetail w={w} />}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}

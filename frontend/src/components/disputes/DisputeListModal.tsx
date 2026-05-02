'use client'

import { ChevronRight } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Pill } from '@/app/profile/components/primitives/Pill'
import type { Dispute, DisputeStatus } from '@/types'
import { DisputeModalShell } from './DisputeModalShell'
import { categoryFor } from './constants'
import { ACTIVE_STATUSES, CLOSED_STATUSES, loadDisputesList } from './useDisputeMutations'

type Tab = 'active' | 'closed' | 'all'

interface DisputeListModalProps {
  open: boolean
  onClose: () => void
  onSelectDispute: (dispute: Dispute) => void
  /**
   * Bumped from outside (e.g. after resolve / send) to force a refetch
   * without re-mounting. Increment to refresh.
   */
  refreshKey?: number
  onShowToast: (msg: string, tone: 'success' | 'error') => void
}

const TABS: ReadonlyArray<{ key: Tab; label: string }> = [
  { key: 'active', label: 'Aktif' },
  { key: 'closed', label: 'Selesai' },
  { key: 'all', label: 'Semua' },
]

const EMPTY_COPY: Record<Tab, string> = {
  active: 'Tiada aduan aktif. Kerja anda licin.',
  closed: 'Tiada aduan yang sudah ditutup.',
  all: 'Belum ada aduan dibuat.',
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'baru-baru ini'
  return d.toLocaleDateString('en-MY', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function statusPillFor(status: DisputeStatus) {
  if (ACTIVE_STATUSES.has(status)) return <Pill tone="amber">{status.replace(/_/g, ' ')}</Pill>
  if (status === 'resolved') return <Pill tone="green">Selesai</Pill>
  if (status === 'closed') return <Pill tone="gray">Tutup</Pill>
  if (status === 'rejected') return <Pill tone="red">Ditolak</Pill>
  if (status === 'escalated') return <Pill tone="purple">Eskalasi</Pill>
  return <Pill tone="gray">{status.replace(/_/g, ' ')}</Pill>
}

export function DisputeListModal({
  open,
  onClose,
  onSelectDispute,
  refreshKey = 0,
  onShowToast,
}: DisputeListModalProps) {
  const [tab, setTab] = useState<Tab>('active')
  const [all, setAll] = useState<Dispute[] | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    loadDisputesList(50)
      .then((data) => { if (!cancelled) setAll(data) })
      .catch((err) => {
        if (!cancelled) {
          setAll([])
          onShowToast(err instanceof Error ? err.message : 'Gagal muat aduan', 'error')
        }
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [open, refreshKey, onShowToast])

  const filtered = useMemo(() => {
    if (!all) return null
    if (tab === 'all') return all
    if (tab === 'active') return all.filter((d) => ACTIVE_STATUSES.has(d.status))
    return all.filter((d) => CLOSED_STATUSES.has(d.status))
  }, [all, tab])

  const counts = useMemo(() => {
    if (!all) return { active: 0, closed: 0, all: 0 }
    return {
      active: all.filter((d) => ACTIVE_STATUSES.has(d.status)).length,
      closed: all.filter((d) => CLOSED_STATUSES.has(d.status)).length,
      all: all.length,
    }
  }, [all])

  return (
    <DisputeModalShell open={open} onClose={onClose} title="Semua aduan" maxWidth={600}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', gap: 6, borderBottom: '0.5px solid var(--border)' }}>
          {TABS.map((t) => {
            const active = tab === t.key
            const count = counts[t.key]
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                aria-pressed={active}
                style={{
                  background: 'transparent',
                  border: 0,
                  borderBottom: active ? '2px solid var(--orange)' : '2px solid transparent',
                  color: active ? 'var(--ink-1)' : 'var(--ink-3)',
                  fontFamily: 'inherit',
                  fontSize: 13,
                  fontWeight: 500,
                  padding: '8px 12px',
                  cursor: 'pointer',
                  letterSpacing: 'inherit',
                }}
              >
                {t.label}{' '}
                <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>{count}</span>
              </button>
            )
          })}
        </div>

        {loading && all === null && (
          <div style={{ padding: 24, textAlign: 'center', fontSize: 13, color: 'var(--ink-3)' }}>
            Memuatkan aduan…
          </div>
        )}

        {filtered !== null && filtered.length === 0 && !loading && (
          <div style={{ padding: 32, textAlign: 'center', fontSize: 13, color: 'var(--ink-3)' }}>
            {EMPTY_COPY[tab]}
          </div>
        )}

        {filtered !== null && filtered.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {filtered.map((d) => {
              const cat = categoryFor(d.category)
              return (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => onSelectDispute(d)}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr auto auto',
                    alignItems: 'center',
                    gap: 12,
                    padding: '12px 14px',
                    background: '#fff',
                    border: '0.5px solid var(--border)',
                    borderRadius: 'var(--r-input)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    letterSpacing: 'inherit',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <code
                        style={{
                          fontFamily: "'Geist Mono', ui-monospace, monospace",
                          fontSize: 12,
                          color: 'var(--ink-1)',
                          fontWeight: 500,
                        }}
                      >
                        #{d.dispute_number}
                      </code>
                      <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>
                        {cat ? `${cat.icon} ${cat.label}` : d.category}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: 'var(--ink-3)',
                        marginTop: 2,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {formatDate(d.updated_at || d.created_at)}
                    </div>
                  </div>
                  {statusPillFor(d.status)}
                  <ChevronRight size={14} strokeWidth={1.5} color="var(--ink-3)" />
                </button>
              )
            })}
          </div>
        )}
      </div>
    </DisputeModalShell>
  )
}

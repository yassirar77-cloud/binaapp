'use client'

import { ChevronRight } from 'lucide-react'
import { Card } from './primitives/Card'
import { LinkBtn } from './primitives/LinkBtn'
import { Pill } from './primitives/Pill'
import { PrimaryButton } from './primitives/PrimaryButton'

export interface Dispute {
  id: string
  displayId: string
  customerName: string
  reason: string
  amount: number | null
  createdAt: string
}

interface DisputeCardProps {
  disputes: Dispute[] | null
  totalOpen: number
  onViewAll: () => void
  onRespond: (dispute: Dispute) => void
}

const BM_MONTHS = [
  'Januari', 'Februari', 'Mac', 'April', 'Mei', 'Jun',
  'Julai', 'Ogos', 'September', 'Oktober', 'November', 'Disember',
]

function formatRelativeBm(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'baru-baru ini'
  const diffMs = Date.now() - d.getTime()
  if (diffMs < 0) return 'baru sekarang'

  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 1) return 'baru sekarang'
  if (minutes < 60) return `${minutes} minit lepas`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} jam lepas`

  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} hari lepas`

  return `${d.getDate()} ${BM_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

function formatAmount(amount: number | null): string {
  if (amount === null || !Number.isFinite(amount)) return '—'
  return `RM${amount.toFixed(2)}`
}

export function DisputeCard({ disputes, totalOpen, onViewAll, onRespond }: DisputeCardProps) {
  if (disputes === null) return null
  if (disputes.length === 0 || totalOpen === 0) return null

  const featured = disputes[0]
  const customer = featured.customerName.trim() || 'Pelanggan'
  const timeAgo = formatRelativeBm(featured.createdAt)

  return (
    <Card warn style={{ background: 'linear-gradient(0deg, #fffaf0 0%, #ffffff 60%)' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: 15, fontWeight: 500, margin: 0 }}>Dispute</h3>
            <Pill tone="amber">{totalOpen} menunggu</Pill>
          </div>
          <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 2 }}>
            Pertikaian dari pelanggan
          </div>
        </div>
        <LinkBtn onClick={onViewAll}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            Lihat semua
            <ChevronRight size={12} strokeWidth={1.5} style={{ display: 'inline-block' }} />
          </span>
        </LinkBtn>
      </div>

      <div
        className="profile-row"
        style={{
          marginTop: 16,
          display: 'grid',
          gridTemplateColumns: '1fr auto auto',
          alignItems: 'center',
          gap: 14,
          padding: '14px 16px',
          background: '#fff',
          border: '0.5px solid var(--border)',
          borderRadius: 10,
        }}
      >
        <div className="profile-row__main" style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <code
              style={{
                fontFamily: "'Geist Mono', ui-monospace, monospace",
                fontSize: 12,
                color: 'var(--ink-1)',
                fontWeight: 500,
              }}
            >
              #{featured.displayId}
            </code>
            <Pill tone="amber">Baru</Pill>
          </div>
          <div
            style={{
              fontSize: 12,
              color: 'var(--ink-3)',
              marginTop: 4,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {customer} · &ldquo;{featured.reason}&rdquo; · {timeAgo}
          </div>
        </div>
        <span
          style={{
            fontSize: 13,
            color: 'var(--ink-1)',
            fontVariantNumeric: 'tabular-nums',
            fontWeight: 500,
          }}
        >
          {formatAmount(featured.amount)}
        </span>
        <PrimaryButton onClick={() => onRespond(featured)} style={{ padding: '7px 12px' }}>
          Jawab
        </PrimaryButton>
      </div>
    </Card>
  )
}

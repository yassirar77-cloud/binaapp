'use client'

import { Card } from './primitives/Card'
import { GhostButton } from './primitives/GhostButton'
import { Pill, type PillTone } from './primitives/Pill'
import { ProgressBar } from './primitives/ProgressBar'

const BM_MONTHS = [
  'Januari', 'Februari', 'Mac', 'April', 'Mei', 'Jun',
  'Julai', 'Ogos', 'September', 'Oktober', 'November', 'Disember',
]

export type PlanTier = 'starter' | 'basic' | 'pro'
export type PlanStatus = 'active' | 'expired' | 'cancelled'

const PRICE: Record<PlanTier, number> = {
  starter: 5,
  basic: 29,
  pro: 49,
} as const

const TIER_DISPLAY: Record<PlanTier, string> = {
  starter: 'Starter',
  basic: 'Basic',
  pro: 'Pro',
}

export interface UsageData {
  used: number
  limit: number | null
  percentage: number
  unlimited: boolean
  addon_credits: number
}

export interface PlanUsage {
  websites: UsageData
  menu_items: UsageData
  ai_hero: UsageData
  ai_images: UsageData
  delivery_zones: UsageData
  riders: UsageData
}

interface PlanCardProps {
  tier: PlanTier
  status: PlanStatus
  endDate: string | null
  isExpired: boolean
  usage: PlanUsage | null
  loading?: boolean
  onUpgrade: () => void
}

interface UsageRow {
  key: keyof PlanUsage
  label: string
  color: string
}

const USAGE_ROWS: UsageRow[] = [
  { key: 'websites',       label: 'Website',          color: 'var(--p-blue)' },
  { key: 'menu_items',     label: 'Menu items',       color: 'var(--p-green)' },
  { key: 'ai_hero',        label: 'AI hero',          color: 'var(--p-purple)' },
  { key: 'ai_images',      label: 'AI images',        color: 'var(--p-coral)' },
  { key: 'delivery_zones', label: 'Zon penghantaran', color: 'var(--p-pink)' },
  { key: 'riders',         label: 'Rider',            color: 'var(--p-amber)' },
]

function formatRenewalDate(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return `${d.getDate()} ${BM_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

function statusPill(status: PlanStatus, isExpired: boolean): { tone: PillTone; label: string; dot: boolean } {
  if (isExpired || status === 'expired') {
    return { tone: 'amber', label: 'Tamat tempoh', dot: false }
  }
  if (status === 'cancelled') {
    return { tone: 'gray', label: 'Dibatalkan', dot: false }
  }
  return { tone: 'green', label: 'Aktif', dot: true }
}

export function PlanCard({
  tier,
  status,
  endDate,
  isExpired,
  usage,
  loading = false,
  onUpgrade,
}: PlanCardProps) {
  const price = PRICE[tier]
  const tierName = TIER_DISPLAY[tier]
  const renewal = formatRenewalDate(endDate)
  const pill = statusPill(status, isExpired)
  const showUpgrade = tier !== 'pro'

  const subtitle = renewal ? `RM${price}/bulan · perbaharui ${renewal}` : `RM${price}/bulan`

  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: 15, fontWeight: 500, margin: 0 }}>Pelan {tierName}</h3>
            <Pill tone={pill.tone} dot={pill.dot}>{pill.label}</Pill>
          </div>
          <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 2 }}>{subtitle}</div>
        </div>
        {showUpgrade && (
          <GhostButton onClick={onUpgrade}>Naik taraf</GhostButton>
        )}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '20px 32px',
          marginTop: 24,
        }}
      >
        {USAGE_ROWS.map((row) => {
          const data = usage?.[row.key]
          const used = data?.used ?? 0
          const limit = data?.limit ?? null
          const unlimited = data?.unlimited ?? false
          const max = unlimited || limit === null ? 'unlimited' : limit
          const limitText = unlimited || limit === null ? 'unlimited' : String(limit)
          return (
            <div key={row.key}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'baseline',
                  marginBottom: 8,
                  gap: 8,
                  minWidth: 0,
                }}
              >
                <span
                  style={{
                    fontSize: 13,
                    color: 'var(--ink-2)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    minWidth: 0,
                  }}
                >
                  {row.label}
                </span>
                <span
                  style={{
                    fontSize: 12,
                    color: 'var(--ink-3)',
                    fontVariantNumeric: 'tabular-nums',
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                  }}
                >
                  {loading ? '—' : (
                    <>
                      {used}
                      <span style={{ color: 'var(--ink-4)' }}>/{limitText}</span>
                    </>
                  )}
                </span>
              </div>
              {loading ? (
                <div
                  style={{
                    height: 3,
                    width: '100%',
                    background: '#eeeff2',
                    borderRadius: 'var(--r-pill)',
                  }}
                />
              ) : (
                <ProgressBar value={used} max={max} color={row.color} />
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}

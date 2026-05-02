'use client'

import type { AvatarTone } from './primitives/Avatar'
import { Avatar } from './primitives/Avatar'
import { Card } from './primitives/Card'
import { GhostButton } from './primitives/GhostButton'
import { Pill } from './primitives/Pill'

export interface Rider {
  id: string
  name: string
  phone: string | null
  vehiclePlate: string | null
  isOnline: boolean
  totalDeliveries: number
}

interface RiderCardProps {
  riders: Rider[] | null
  onAdd: () => void
  onManage: (rider: Rider) => void
}

const RIDER_TONES: readonly AvatarTone[] = ['teal', 'amber', 'purple'] as const

function avatarTone(seed: string): AvatarTone {
  const lower = seed.toLowerCase()
  let sum = 0
  for (let i = 0; i < lower.length; i++) sum += lower.charCodeAt(i)
  return RIDER_TONES[sum % RIDER_TONES.length]
}

function avatarInitial(rider: Rider): string {
  const name = (rider.name ?? '').trim()
  if (name) return name[0].toUpperCase()
  const phone = (rider.phone ?? '').trim()
  if (phone) {
    const firstDigit = phone.split('').find((c) => /\d/.test(c))
    if (firstDigit) return firstDigit
  }
  return '?'
}

function subtitleParts(phone: string | null, plate: string | null): string {
  const left = phone?.trim() || '—'
  const right = plate?.trim() || '—'
  return `${left} · ${right}`
}

export function RiderCard({ riders, onAdd, onManage }: RiderCardProps) {
  const loading = riders === null
  const total = riders?.length ?? 0
  const onlineCount = riders?.filter((r) => r.isOnline).length ?? 0
  const isEmpty = !loading && total === 0

  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <h3 style={{ fontSize: 15, fontWeight: 500, margin: 0 }}>Pasukan rider</h3>
          <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 2 }}>
            {loading ? 'Memuatkan…' : `${total} rider · ${onlineCount} online sekarang`}
          </div>
        </div>
        <GhostButton onClick={onAdd}>+ Tambah</GhostButton>
      </div>

      {loading && (
        <div style={{ marginTop: 16 }}>
          {[0, 1].map((i) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: 'auto 1fr auto',
                alignItems: 'center',
                gap: 14,
                padding: '14px 0',
                borderTop: '0.5px solid var(--border)',
              }}
            >
              <div style={{ width: 38, height: 38, borderRadius: '50%', background: '#eeeff2' }} />
              <div>
                <div style={{ height: 12, width: 100, background: '#eeeff2', borderRadius: 4 }} />
                <div
                  style={{
                    height: 10,
                    width: 140,
                    background: '#eeeff2',
                    borderRadius: 4,
                    marginTop: 6,
                  }}
                />
              </div>
              <div style={{ height: 14, width: 56, background: '#eeeff2', borderRadius: 4 }} />
            </div>
          ))}
        </div>
      )}

      {isEmpty && (
        <div
          style={{
            marginTop: 16,
            padding: '20px 0',
            textAlign: 'center',
            fontSize: 13,
            color: 'var(--ink-3)',
          }}
        >
          Belum ada rider
        </div>
      )}

      {!loading && !isEmpty && (
        <div style={{ marginTop: 16 }}>
          {riders.map((rider) => {
            const hasName = rider.name?.trim().length > 0
            const tone = avatarTone(hasName ? rider.name : rider.id)
            return (
              <div
                key={rider.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'auto 1fr auto auto',
                  alignItems: 'center',
                  gap: 14,
                  padding: '14px 0',
                  borderTop: '0.5px solid var(--border)',
                }}
              >
                <Avatar initials={avatarInitial(rider)} tone={tone} size={38} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    {hasName ? (
                      <span style={{ fontSize: 14, color: 'var(--ink-1)', fontWeight: 500 }}>
                        {rider.name}
                      </span>
                    ) : (
                      <span
                        style={{
                          fontSize: 14,
                          color: 'var(--ink-3)',
                          fontWeight: 500,
                          fontStyle: 'italic',
                        }}
                      >
                        Rider tanpa nama
                      </span>
                    )}
                    {rider.isOnline ? (
                      <Pill tone="green" dot>Online</Pill>
                    ) : (
                      <Pill tone="gray">Offline</Pill>
                    )}
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
                    {subtitleParts(rider.phone, rider.vehiclePlate)}
                  </div>
                </div>
                <div style={{ textAlign: 'right', minWidth: 90 }}>
                  <div
                    style={{
                      fontSize: 13,
                      color: 'var(--ink-1)',
                      fontVariantNumeric: 'tabular-nums',
                      fontWeight: 500,
                    }}
                  >
                    {rider.totalDeliveries}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--ink-3)' }}>hantaran</div>
                </div>
                <GhostButton onClick={() => onManage(rider)}>Urus</GhostButton>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}

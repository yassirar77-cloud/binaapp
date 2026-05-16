'use client'

import { AlertCircle, Check, MapPin } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { CoveredZone } from '../checkout-api'

export type CoverageStatus =
  | 'idle'
  | 'checking'
  | 'covered'
  | 'uncovered'
  | 'error'

interface CoverageStatusSectionProps {
  status: CoverageStatus
  zone: CoveredZone | null
  /** Cart subtotal in RM. Used to validate the detected ring's minOrder. */
  subtotal: number
  /** Free-form error message when status === 'error'. */
  error?: string | null
  step?: number
}

/**
 * Section 3 — auto-detected delivery zone display. Replaces the old
 * customer-picks-a-zone dropdown. The covering ring is resolved
 * server-side from the customer's delivery lat/lng via the public
 * /api/v1/delivery/zones/{id}/cover endpoint; this component is a pure
 * presentation layer over its result.
 *
 * Five states:
 *   idle       — no coords yet (customer hasn't geo'd or "Semak alamat"-ed).
 *   checking   — request in flight.
 *   covered    — ring resolved; show name + fee + min-order line.
 *   uncovered  — coords resolved but no ring covers them; block CTA.
 *   error      — backend / network failure; surface message with retry hint.
 */
export function CoverageStatusSection({
  status,
  zone,
  subtotal,
  error = null,
  step = 3,
}: CoverageStatusSectionProps) {
  const minOrderShortfall =
    zone && zone.minOrder > 0 && subtotal < zone.minOrder
      ? zone.minOrder - subtotal
      : 0

  const filled = status === 'covered' && minOrderShortfall === 0

  return (
    <div className="co-sec fade-up" style={{ animationDelay: '80ms' }}>
      <div className="co-sec-head">
        <h2>
          <span className={cn('num', filled && 'done')}>{step}</span>
          Kawasan penghantaran
        </h2>
      </div>

      {status === 'idle' && (
        <div style={{ fontSize: 13, color: 'var(--fg-muted)' }}>
          Sila pilih alamat atau gunakan lokasi semasa untuk menyemak liputan.
        </div>
      )}

      {status === 'checking' && (
        <div style={{ fontSize: 13, color: 'var(--fg-muted)' }}>
          Menyemak liputan…
        </div>
      )}

      {status === 'covered' && zone && (
        <>
          <div className="zone-covered">
            <Check size={14} strokeWidth={3} aria-hidden="true" />
            <span>
              Penghantaran ke <strong>{zone.name}</strong> — RM {zone.fee.toFixed(2)}
            </span>
          </div>
          {zone.minOrder > 0 && (
            <div className="zone-meta">
              <MapPin size={12} aria-hidden="true" />
              <span>Min. RM {zone.minOrder.toFixed(2)}</span>
            </div>
          )}
          {minOrderShortfall > 0 && (
            <div className="zone-error" role="alert">
              <AlertCircle size={14} aria-hidden="true" />
              <span>
                Minimum pesanan untuk zon ini ialah RM {zone.minOrder.toFixed(2)}.
                Tambah RM {minOrderShortfall.toFixed(2)} lagi.
              </span>
            </div>
          )}
        </>
      )}

      {status === 'uncovered' && (
        <div className="zone-error" role="alert">
          <AlertCircle size={14} aria-hidden="true" />
          <span>Maaf, lokasi anda di luar kawasan penghantaran restoran ini.</span>
        </div>
      )}

      {status === 'error' && (
        <div className="zone-error" role="alert">
          <AlertCircle size={14} aria-hidden="true" />
          <span>{error ?? 'Tidak dapat menyemak liputan. Sila cuba lagi.'}</span>
        </div>
      )}
    </div>
  )
}

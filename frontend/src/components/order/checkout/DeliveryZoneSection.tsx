'use client'

import { AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DeliveryZone } from '../checkout-api'

interface DeliveryZoneSectionProps {
  zones: DeliveryZone[]
  selectedZoneId: string | null
  onSelect: (id: string) => void
  /** Cart subtotal in RM. Used to validate the selected zone's minimum_order. */
  subtotal: number
  step?: number
  /** Loading state when zones haven't been fetched yet. */
  loading?: boolean
  /** Error state from the zones fetch. */
  error?: string | null
}

/**
 * Section 3 — pick a delivery zone. Shows the zone name, fee, and ETA
 * range. If the customer's cart subtotal is below the selected zone's
 * `minimum_order`, surfaces an inline error. The "place order" button
 * (PlaceOrderCTA) reads the same min-order check and disables itself.
 *
 * TODO(zones): Add auto-suggest zone based on detected location once
 *              we have GPS coords from the geolocation helper.
 */
export function DeliveryZoneSection({
  zones,
  selectedZoneId,
  onSelect,
  subtotal,
  step = 3,
  loading = false,
  error = null,
}: DeliveryZoneSectionProps) {
  const selected = zones.find((z) => z.id === selectedZoneId) ?? null
  const minOrderShortfall =
    selected && selected.minOrder > 0 && subtotal < selected.minOrder
      ? selected.minOrder - subtotal
      : 0

  const filled = !!selected && minOrderShortfall === 0

  return (
    <div className="co-sec fade-up" style={{ animationDelay: '80ms' }}>
      <div className="co-sec-head">
        <h2>
          <span className={cn('num', filled && 'done')}>{step}</span>
          Kawasan penghantaran
        </h2>
      </div>

      {loading ? (
        <div style={{ fontSize: 13, color: 'var(--fg-muted)' }}>Memuatkan zon…</div>
      ) : error ? (
        <div className="zone-error">
          <AlertCircle size={14} aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : zones.length === 0 ? (
        <div className="zone-error">
          <AlertCircle size={14} aria-hidden="true" />
          <span>Restoran ini belum tetapkan zon penghantaran.</span>
        </div>
      ) : (
        <>
          <select
            className="zone-select"
            value={selectedZoneId ?? ''}
            onChange={(e) => onSelect(e.target.value)}
            aria-label="Kawasan penghantaran"
          >
            <option value="">Pilih kawasan…</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name} · RM {z.fee.toFixed(2)}
              </option>
            ))}
          </select>

          {selected && (
            <div className="zone-meta">
              <span>
                Anggaran tiba {selected.etaMin}-{selected.etaMax} minit
              </span>
              {selected.minOrder > 0 && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>Min. RM {selected.minOrder.toFixed(2)}</span>
                </>
              )}
            </div>
          )}

          {minOrderShortfall > 0 && (
            <div className="zone-error" role="alert">
              <AlertCircle size={14} aria-hidden="true" />
              <span>
                Minimum pesanan untuk zon ini ialah RM {selected!.minOrder.toFixed(2)}.
                Tambah RM {minOrderShortfall.toFixed(2)} lagi.
              </span>
            </div>
          )}
        </>
      )}
    </div>
  )
}

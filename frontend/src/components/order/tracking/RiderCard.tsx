'use client'

import { Phone } from 'lucide-react'
import toast from 'react-hot-toast'
import { nameInitials } from '../phone'
import type { TrackedOrder, TrackedRider } from '../tracking-api'

interface RiderCardProps {
  rider: TrackedRider
  order: TrackedOrder
}

/**
 * Compact rider info row shown when a rider is assigned to the order.
 * Two CTAs:
 *   - tel: native dialer
 *   - https://wa.me/{phone}?text=... — WhatsApp deep link with a
 *     prefilled "Hi, saya pesanan #ORD-XXXX" message in BM
 *
 * Both fall back to copying the phone number to the clipboard if the
 * device refuses to open the link (some desktop browsers ignore tel:).
 */
export function RiderCard({ rider, order }: RiderCardProps) {
  const wa = toWaMeNumber(rider.phone)
  const tel = toTelNumber(rider.phone)
  const message = `Hi, saya pesanan #${order.orderNumber}`

  const copyOnFail = (val: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(val).catch(() => undefined)
      toast(`Nombor disalin: ${val}`, { duration: 2500 })
    }
  }

  return (
    <div className="rider-card fade-up">
      <div className="rider-av" aria-hidden="true">
        {rider.photoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={rider.photoUrl} alt="" loading="lazy" decoding="async" />
        ) : (
          nameInitials(rider.name) || 'R'
        )}
      </div>
      <div className="rider-info">
        <div className="nm">{rider.name}</div>
        <div className="meta">
          {typeof rider.rating === 'number' && rider.rating > 0 && (
            <span>★ {rider.rating.toFixed(1)}</span>
          )}
          {rider.vehiclePlate && <span className="plate">{rider.vehiclePlate}</span>}
          {rider.vehicleType && <span>{rider.vehicleType}</span>}
        </div>
      </div>
      <div className="rider-actions">
        {tel && (
          <a
            className="ic-btn"
            href={`tel:${tel}`}
            aria-label={`Hubungi ${rider.name}`}
            onClick={() => {
              // Some browsers ignore tel: silently — clipboard fallback.
              setTimeout(() => copyOnFail(rider.phone), 600)
            }}
          >
            <Phone size={16} strokeWidth={2} aria-hidden="true" />
          </a>
        )}
        {wa && (
          <a
            className="ic-btn wa"
            href={`https://wa.me/${wa}?text=${encodeURIComponent(message)}`}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`WhatsApp ${rider.name}`}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M17.6 6.32A8 8 0 0 0 4.5 16l-1 4 4.1-1A8 8 0 1 0 17.6 6.32zM12 18.3a6.4 6.4 0 0 1-3.3-.9l-2.4.6.6-2.3-.1-.2a6.4 6.4 0 1 1 5.2 2.8zm3.5-4.8c-.2-.1-1.1-.6-1.3-.6-.2-.1-.3-.1-.4.1-.1.2-.5.6-.6.7-.1.1-.2.1-.4 0-.2-.1-.8-.3-1.5-.9-.6-.5-1-1.2-1.1-1.4-.1-.2 0-.3.1-.4.1-.1.2-.2.3-.4.1-.1.1-.2.2-.3 0-.1 0-.2 0-.3 0-.1-.4-1-.6-1.4-.1-.3-.3-.3-.4-.3h-.4c-.1 0-.3 0-.5.2-.2.2-.7.6-.7 1.6 0 .9.7 1.8.8 1.9.1.1 1.4 2.2 3.5 3.1.5.2.9.3 1.2.4.5.2.9.1 1.3.1.4-.1 1.1-.5 1.3-.9.2-.5.2-.9.1-.9-.1-.2-.2-.2-.4-.3z" />
            </svg>
          </a>
        )}
      </div>
    </div>
  )
}

/* ----- Phone helpers ---------------------------------------------------- */

/**
 * Convert any Malaysian phone form to E.164-without-plus for `wa.me`.
 *   "0123456789"   → "60123456789"
 *   "60123456789"  → "60123456789"
 *   "+60123456789" → "60123456789"
 */
export function toWaMeNumber(raw: string): string {
  const digits = (raw || '').replace(/\D/g, '')
  if (!digits) return ''
  if (digits.startsWith('60')) return digits
  if (digits.startsWith('0')) return `60${digits.slice(1)}`
  return `60${digits}`
}

/** Same as `toWaMeNumber` but with the leading `+`. */
export function toTelNumber(raw: string): string {
  const wa = toWaMeNumber(raw)
  return wa ? `+${wa}` : ''
}

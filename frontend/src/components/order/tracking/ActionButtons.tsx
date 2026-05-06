'use client'

import { AlertTriangle, MessageCircle } from 'lucide-react'
import Link from 'next/link'

interface ActionButtonsProps {
  orderNumber: string
  /** WhatsApp number for the restaurant. Optional — falls back to a no-op. */
  restaurantPhone?: string
}

/**
 * Two ghost buttons at the bottom of the tracking page:
 *   - "Hubungi restoran" → wa.me deep link if a phone is provided,
 *     otherwise a no-op stub (rare in production).
 *   - "Ada masalah?" → /order/{order_number}/dispute (PR 7 territory,
 *     route 404s today).
 */
export function ActionButtons({ orderNumber, restaurantPhone }: ActionButtonsProps) {
  const wa = restaurantPhone
    ? `https://wa.me/${(restaurantPhone || '').replace(/\D/g, '')}?text=${encodeURIComponent(`Hi, saya pesanan #${orderNumber}`)}`
    : null

  return (
    <div className="tk-actions">
      {wa ? (
        <a className="action-btn" href={wa} target="_blank" rel="noopener noreferrer">
          <MessageCircle size={14} strokeWidth={2} aria-hidden="true" />
          Hubungi restoran
        </a>
      ) : (
        <button type="button" className="action-btn" disabled>
          <MessageCircle size={14} strokeWidth={2} aria-hidden="true" />
          Hubungi restoran
        </button>
      )}
      <Link
        className="action-btn warn"
        href={`/order/${encodeURIComponent(orderNumber)}/dispute`}
      >
        <AlertTriangle size={14} strokeWidth={2} aria-hidden="true" />
        Ada masalah?
      </Link>
    </div>
  )
}

'use client'

import { AlertTriangle, MessageCircle } from 'lucide-react'
import Link from 'next/link'
import { useRestaurantStore } from '../restaurant-store'

interface ActionButtonsProps {
  orderNumber: string
}

/**
 * Two ghost buttons at the bottom of the tracking page:
 *   - "Hubungi restoran" → opens a WhatsApp deep link to the
 *     restaurant's WhatsApp number (sourced from the restaurant
 *     store, populated by the by-domain lookup). Hidden entirely
 *     when the restaurant has not configured a WhatsApp number.
 *   - "Ada masalah?" → /order/{order_number}/dispute.
 */
export function ActionButtons({ orderNumber }: ActionButtonsProps) {
  const whatsappNumber = useRestaurantStore((s) => s.restaurant?.whatsappNumber ?? null)
  const phone = whatsappNumber?.replace(/\D/g, '') || null

  const handleContactRestaurant = () => {
    if (!phone) return
    const message = `Hai! Pasal pesanan ${orderNumber}`
    window.open(
      `https://wa.me/${phone}?text=${encodeURIComponent(message)}`,
      '_blank',
      'noopener,noreferrer'
    )
  }

  return (
    <div className="tk-actions">
      {phone && (
        <button type="button" className="action-btn" onClick={handleContactRestaurant}>
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

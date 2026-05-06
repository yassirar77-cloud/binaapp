import type { Metadata } from 'next'
import { TrackingPageClient } from '@/components/order/tracking/TrackingPageClient'

export const metadata: Metadata = {
  title: 'Jejak pesanan · BinaApp Delivery',
  description: 'Jejak status pesanan anda secara langsung.',
}

interface PageProps {
  params: { orderNumber: string }
}

/**
 * Tracking page route. The dynamic segment is named `orderNumber`
 * because the underlying GET /api/v1/delivery/orders/{order_number}
 * /track endpoint is keyed by the human-readable order number
 * (e.g. "ORD-3847"), NOT the order's UUID.
 *
 * PR 5's checkout already redirects to /order/{order_number}/track on
 * successful placement.
 */
export default function TrackOrderPage({ params }: PageProps) {
  // Decode in case the order number contains characters that needed
  // URL encoding (it shouldn't, but defensive).
  const orderNumber = decodeURIComponent(params.orderNumber)
  return <TrackingPageClient orderNumber={orderNumber} />
}

import type { Metadata } from 'next'
import { TrackingPageClient } from '@/components/order/tracking/TrackingPageClient'

export const metadata: Metadata = {
  title: 'Jejak pesanan · BinaApp Delivery',
  description: 'Jejak status pesanan anda secara langsung.',
}

interface PageProps {
  params: { order_number: string }
}

export default function TrackOrderPage({ params }: PageProps) {
  const orderNumber = decodeURIComponent(params.order_number)
  return <TrackingPageClient orderNumber={orderNumber} />
}

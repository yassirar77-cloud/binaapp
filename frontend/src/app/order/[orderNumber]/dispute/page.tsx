import type { Metadata } from 'next'
import { DisputePageClient } from '@/components/order/dispute/DisputePageClient'

export const metadata: Metadata = {
  title: 'Lapor masalah · BinaApp Delivery',
  description: 'Beritahu kami apa yang berlaku — kami akan bantu selesaikan.',
}

interface PageProps {
  params: { orderNumber: string }
}

/**
 * Dispute reporting page. URL pattern matches the tracking page:
 * `/order/{order_number}/dispute`. The orchestrator fetches the
 * order on mount (via the same `/track` endpoint PR 6 uses) to
 * resolve the order UUID needed by the dispute-create call.
 */
export default function DisputeOrderPage({ params }: PageProps) {
  const orderNumber = decodeURIComponent(params.orderNumber)
  return <DisputePageClient orderNumber={orderNumber} />
}

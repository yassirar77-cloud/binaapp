'use client'

import { ChevronLeft } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface DisputeHeaderProps {
  /** Page title — switches to "Aduan dihantar" once submission lands. */
  title?: string
  orderNumber: string
}

/**
 * Sticky header for the dispute page. Back button routes to the
 * tracking page for the same order.
 */
export function DisputeHeader({ title = 'Lapor masalah', orderNumber }: DisputeHeaderProps) {
  const router = useRouter()
  return (
    <div className="dp-header">
      <button
        type="button"
        className="back-btn"
        onClick={() => router.push(`/order/${encodeURIComponent(orderNumber)}/track`)}
        aria-label="Kembali ke pesanan"
      >
        <ChevronLeft size={16} strokeWidth={2.2} aria-hidden="true" />
      </button>
      <h1>{title}</h1>
    </div>
  )
}

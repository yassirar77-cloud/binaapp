'use client'

import { ChevronLeft } from 'lucide-react'
import { useRouter } from 'next/navigation'

/**
 * Top of the checkout page: back button → /order/cart, page title,
 * tiny step pip on the right (4 / 6 in the design — this is the 4th
 * step in the 6-page customer flow).
 */
export function CheckoutHeader() {
  const router = useRouter()
  return (
    <div className="co-header">
      <button
        type="button"
        className="back-btn"
        onClick={() => router.push('/order/cart')}
        aria-label="Kembali ke keranjang"
      >
        <ChevronLeft size={16} strokeWidth={2.2} aria-hidden="true" />
      </button>
      <h1>Checkout</h1>
      <span className="step">4 / 6</span>
    </div>
  )
}

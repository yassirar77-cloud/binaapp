'use client'

import { X } from 'lucide-react'
import { useRouter } from 'next/navigation'

/**
 * Sticky cart-sheet header. Title on the left, close X on the right
 * which routes back to /order/menu (the cart sheet is conceptually a
 * modal over the menu — closing returns the customer to browsing).
 */
export function CartHeader() {
  const router = useRouter()
  return (
    <div className="cart-header">
      <h1>Keranjang anda</h1>
      <button
        type="button"
        className="close-btn"
        onClick={() => router.push('/order/menu')}
        aria-label="Tutup keranjang"
      >
        <X size={16} strokeWidth={2.2} aria-hidden="true" />
      </button>
    </div>
  )
}

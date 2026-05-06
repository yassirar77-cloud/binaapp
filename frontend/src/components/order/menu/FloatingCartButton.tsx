'use client'

import { ShoppingCart } from 'lucide-react'
import { useCartCount, useCartTotal } from '../cart-store'

interface FloatingCartButtonProps {
  onClick: () => void
  /** Hide the FAB while the item-detail sheet is open. */
  hidden?: boolean
}

/**
 * Bottom-pinned FAB that surfaces the cart count + total. Hidden when
 * the cart is empty OR while the item detail sheet is open (the sheet
 * already overlays the bottom area, so the FAB would clash).
 */
export function FloatingCartButton({ onClick, hidden = false }: FloatingCartButtonProps) {
  const count = useCartCount()
  const total = useCartTotal()

  if (count === 0 || hidden) return null

  return (
    <button
      type="button"
      className="fab fade-up"
      onClick={onClick}
      aria-label={`Lihat keranjang · ${count} item · RM ${total.toFixed(2)}`}
    >
      <span className="left">
        <ShoppingCart size={18} aria-hidden="true" />
        <span className="badge">{count}</span>
        Lihat keranjang
      </span>
      <span className="total">RM {total.toFixed(2)}</span>
    </button>
  )
}

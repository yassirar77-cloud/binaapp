'use client'

import { ArrowRight } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Button } from '../primitives'
import { useCartCount, useCartGrandTotal } from '../cart-store'

/**
 * Sticky bottom button. Routes to /order/checkout (PR 5 territory —
 * the route 404s today; the customer-flow state is fully persisted
 * at this point so the next page can read it on mount).
 *
 * Disabled if the cart is empty (defensive — the page also renders
 * <EmptyCart> in that case so this branch is unreachable, but keeping
 * it makes the component safe to drop anywhere).
 */
export function CheckoutCTA() {
  const router = useRouter()
  const total = useCartGrandTotal()
  const count = useCartCount()

  return (
    <div className="checkout-bar">
      <Button
        disabled={count === 0}
        onClick={() => router.push('/order/checkout')}
      >
        Ke checkout · RM {total.toFixed(2)}
        <ArrowRight size={18} aria-hidden="true" />
      </Button>
    </div>
  )
}

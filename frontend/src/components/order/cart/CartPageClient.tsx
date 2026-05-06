'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useCartItems } from '../cart-store'
import { useCustomerStore } from '../customer-store'
import { useRestaurant } from '../ThemeProvider'
import { CartHeader } from './CartHeader'
import { CartItemRow } from './CartItemRow'
import { CartSummary } from './CartSummary'
import { CheckoutCTA } from './CheckoutCTA'
import { EmptyCart } from './EmptyCart'
import { KitchenNotesInput } from './KitchenNotesInput'
import { PromoCodeInput } from './PromoCodeInput'

/**
 * Cart page orchestrator.
 *
 * Two render modes — empty cart (single CTA back to menu) vs populated
 * cart (item list + notes + promo + summary + sticky checkout).
 *
 * On mount this component:
 *   1. Adds the `cart-route` class to the parent `.order-flow` wrapper
 *      so the page background flips to the dark "modal" backdrop. The
 *      class is removed on unmount so leaving the cart doesn't poison
 *      neighbouring pages.
 *   2. Redirects to /order/identify if the customer hasn't been
 *      identified yet — same pattern PR 3's menu page uses.
 */
export function CartPageClient() {
  const router = useRouter()
  const restaurant = useRestaurant()
  const customer = useCustomerStore((s) => s.customer)
  const items = useCartItems()

  const [hydrated, setHydrated] = useState(false)

  // ---- Toggle the dark backdrop on the .order-flow wrapper while
  //      this page is mounted. Done in a layout effect so the class
  //      lands before the first paint.
  useEffect(() => {
    const flow = document.querySelector('.order-flow')
    if (!flow) return
    flow.classList.add('cart-route')
    return () => {
      flow.classList.remove('cart-route')
    }
  }, [])

  // ---- Hydration gate (Zustand persist hasn't filled the store yet
  //      on the SSR'd first paint).
  useEffect(() => {
    setHydrated(true)
  }, [])

  // ---- Customer identity guard.
  useEffect(() => {
    if (!hydrated) return
    if (!customer?.phone) {
      router.replace('/order/identify')
    }
  }, [hydrated, customer?.phone, router])

  // Avoid flashing the cart UI for users we're about to redirect.
  if (hydrated && !customer?.phone) {
    return null
  }

  // ---- Empty cart branch.
  if (hydrated && items.length === 0) {
    return (
      <div className="cart-sheet">
        <div className="cart-grip" aria-hidden="true" />
        <CartHeader />
        <EmptyCart />
      </div>
    )
  }

  // ---- Pre-hydration shell — render the chrome but no items, so the
  //      sheet still slides up cleanly while the store rehydrates.
  return (
    <div className="cart-sheet">
      <div className="cart-grip" aria-hidden="true" />
      <CartHeader />

      <div className="cart-meta">
        <div className="resto-mini" aria-hidden="true">
          {restaurant.initials}
        </div>
        <span>{restaurant.name}</span>
      </div>

      <div className="cart-items">
        {items.map((item) => (
          <CartItemRow key={item.id} item={item} />
        ))}
      </div>

      <KitchenNotesInput />

      <div className="promo-section">
        <PromoCodeInput />
      </div>

      <CartSummary />

      <CheckoutCTA />
    </div>
  )
}

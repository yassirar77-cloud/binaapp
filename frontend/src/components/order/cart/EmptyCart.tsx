'use client'

import { ShoppingCart } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Button } from '../primitives'
import { useRestaurant } from '../ThemeProvider'

/**
 * Empty cart state. Shown when `cart.items.length === 0`. Single CTA
 * routes back to the menu.
 */
export function EmptyCart() {
  const router = useRouter()
  const restaurant = useRestaurant()

  return (
    <div className="empty-cart">
      <div className="ic">
        <ShoppingCart size={28} strokeWidth={1.5} aria-hidden="true" />
      </div>
      <h2>Keranjang masih kosong</h2>
      <p>Mari pilih makanan kegemaran anda dari {restaurant.short}.</p>
      <div style={{ maxWidth: 220, margin: '0 auto' }}>
        <Button onClick={() => router.push('/order/menu')}>Lihat menu</Button>
      </div>
    </div>
  )
}

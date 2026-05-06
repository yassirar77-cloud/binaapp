import type { Metadata } from 'next'
import { CartPageClient } from '@/components/order/cart/CartPageClient'

export const metadata: Metadata = {
  title: 'Keranjang · BinaApp Delivery',
  description: 'Semak pesanan anda sebelum checkout.',
}

/**
 * Cart page — fully client-side state (cart items, notes, promo all
 * live in Zustand + localStorage), so the server component is a thin
 * shell that hands off to <CartPageClient>.
 *
 * The dark "modal" backdrop is applied via a class on the `.order-flow`
 * wrapper from inside <CartPageClient> so it cleans itself up on
 * unmount.
 */
export default function CartPage() {
  return <CartPageClient />
}

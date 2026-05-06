import type { Metadata } from 'next'
import { CheckoutPageClient } from '@/components/order/checkout/CheckoutPageClient'

export const metadata: Metadata = {
  title: 'Checkout · BinaApp Delivery',
  description: 'Sahkan pesanan dan alamat penghantaran anda.',
}

/**
 * Checkout page — fully client-side state (cart + customer come from
 * Zustand, zones are fetched on mount). The server component is a
 * thin shell. The page-background flip is handled inside
 * CheckoutPageClient via a `checkout-route` class on `.order-flow`.
 */
export default function CheckoutPage() {
  return <CheckoutPageClient />
}

import type { Metadata } from 'next'
import { MenuPageClient } from '@/components/order/menu/MenuPageClient'

export const metadata: Metadata = {
  title: 'Menu · BinaApp Delivery',
  description: 'Pilih makanan kegemaran anda untuk tempah.',
}

export const dynamic = 'force-dynamic'

/**
 * Menu page.
 *
 * SSR menu fetch was removed because the restaurant ID is now resolved
 * client-side from the `?r=` query parameter (stored in Zustand).
 * MenuPageClient handles the initial fetch on mount using the resolved
 * restaurant from context.
 */
export default function MenuPage() {
  return <MenuPageClient initialMenu={null} />
}

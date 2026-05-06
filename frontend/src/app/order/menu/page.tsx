import type { Metadata } from 'next'
import { DEFAULT_RESTAURANT } from '@/components/order/ThemeProvider'
import { MenuPageClient } from '@/components/order/menu/MenuPageClient'
import { fetchMenu, MenuFetchError } from '@/components/order/menu-api'

export const metadata: Metadata = {
  title: 'Menu · BinaApp Delivery',
  description: 'Pilih makanan kegemaran anda untuk tempah.',
}

// SSR — keep the menu page dynamic so price/availability changes
// surface immediately without a redeploy. Same intent as the
// `cache: 'no-store'` flag in `fetchMenu`.
export const dynamic = 'force-dynamic'

export default async function MenuPage() {
  // PR 3 still uses the hardcoded DEFAULT_RESTAURANT stub from PR 1.
  // Real subdomain resolution lands in a later PR.
  const restaurant = DEFAULT_RESTAURANT

  let initialMenu = null
  let initialError: string | null = null
  try {
    initialMenu = await fetchMenu(restaurant.websiteId)
  } catch (err) {
    initialError =
      err instanceof MenuFetchError
        ? err.message
        : 'Tidak dapat memuatkan menu. Cuba lagi sebentar.'
  }

  return <MenuPageClient initialMenu={initialMenu} initialError={initialError} />
}

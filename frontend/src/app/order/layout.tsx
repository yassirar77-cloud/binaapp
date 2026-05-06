import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { DEFAULT_RESTAURANT, ThemeProvider } from '@/components/order/ThemeProvider'
import './theme.css'

export const metadata: Metadata = {
  title: 'BinaApp Delivery',
  description: 'Tempah makanan dari restoran kegemaran anda.',
}

export default function OrderLayout({ children }: { children: ReactNode }) {
  // PR 1: hardcoded default restaurant. Real subdomain resolution lands in PR 2+.
  const restaurant = DEFAULT_RESTAURANT

  return <ThemeProvider restaurant={restaurant}>{children}</ThemeProvider>
}

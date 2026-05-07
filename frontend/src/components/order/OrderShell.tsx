'use client'

import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { DEFAULT_RESTAURANT, ThemeProvider } from './ThemeProvider'
import { useRestaurantStore } from './restaurant-store'
import type { RestaurantTheme } from './types'

/**
 * Client wrapper for the /order/* layout.
 *
 * 1. Rehydrates the restaurant Zustand store from localStorage on mount
 *    (using `skipHydration` to avoid SSR mismatch).
 * 2. Derives the active `RestaurantTheme` from the store — or falls back
 *    to `DEFAULT_RESTAURANT` if no restaurant has been resolved yet
 *    (keeps the dev/showcase flow working without `?r=`).
 * 3. Renders a minimal skeleton during hydration to prevent a flash of
 *    wrong-restaurant content.
 */
export function OrderShell({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    useRestaurantStore.persist.rehydrate()
    setHydrated(true)
  }, [])

  const resolved = useRestaurantStore((s) => s.restaurant)

  if (!hydrated) {
    return (
      <div className="order-flow" style={{ minHeight: '100dvh' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100dvh',
          }}
        >
          <div style={{ width: 48, height: 48, borderRadius: '50%', background: '#EEEEF3' }} />
        </div>
      </div>
    )
  }

  const restaurant: RestaurantTheme = resolved
    ? {
        websiteId: resolved.id,
        name: resolved.businessName || resolved.name,
        short: resolved.name,
        initials: deriveInitials(resolved.businessName || resolved.name),
        cuisine: '',
        status: 'open',
        brandPrimary: '#E8501F',
        brandPrimaryHover: '#C53F12',
        brandPrimaryFg: '#FFFFFF',
        brandSecondary: '#FFD46B',
      }
    : DEFAULT_RESTAURANT

  return <ThemeProvider restaurant={restaurant}>{children}</ThemeProvider>
}

function deriveInitials(name: string): string {
  const words = name.trim().split(/\s+/)
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

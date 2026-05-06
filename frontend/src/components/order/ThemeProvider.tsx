'use client'

import { createContext, useContext, useMemo } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { RestaurantTheme } from './types'

/**
 * Hardcoded default for PR 2 — gives the customer-flow a real `website_id`
 * so end-to-end calls against `/api/v1/customers/lookup` work on the
 * Vercel preview without needing subdomain resolution wired up.
 *
 * The UUID below is the `mitora` test website that's already in
 * production with menu data.
 *
 * TODO(restaurant): Replace this hardcoded mitora website ID with real
 * subdomain resolution from middleware (e.g. `pelita.binaapp.my` ->
 * websites.slug='pelita') in a later PR.
 *
 * TODO(restaurant): Add brand_primary, brand_primary_hover, brand_primary_fg,
 * brand_secondary columns to the `websites` table — currently hardcoded.
 */
export const DEFAULT_RESTAURANT: RestaurantTheme = {
  websiteId: '3dc0420c-fbd4-4262-82bd-aca42724af84',
  name: 'Nasi Kandar Pelita',
  short: 'Pelita',
  initials: 'NP',
  cuisine: 'Mamak · Indian Muslim',
  status: 'open',
  brandPrimary: '#E8501F',
  brandPrimaryHover: '#C53F12',
  brandPrimaryFg: '#FFFFFF',
  brandSecondary: '#FFD46B',
}

/** Defaults used when a restaurant ships a malformed brand color. */
const FALLBACK_PRIMARY = '#E8501F'
const FALLBACK_PRIMARY_HOVER = '#C53F12'
const FALLBACK_PRIMARY_FG = '#FFFFFF'
const FALLBACK_SECONDARY = '#FFD46B'

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/

const safeColor = (input: string | undefined, fallback: string): string =>
  input && HEX_RE.test(input.trim()) ? input.trim() : fallback

interface ThemeProviderProps {
  restaurant: RestaurantTheme
  className?: string
  children: ReactNode
}

const RestaurantContext = createContext<RestaurantTheme | null>(null)

/**
 * Hook for accessing the current restaurant from anywhere inside the
 * customer-flow tree. Throws if called outside a `<ThemeProvider>`.
 */
export function useRestaurant(): RestaurantTheme {
  const ctx = useContext(RestaurantContext)
  if (!ctx) {
    throw new Error(
      'useRestaurant must be used inside <ThemeProvider> (in /order/* routes)'
    )
  }
  return ctx
}

/**
 * Wraps the customer-flow tree, scopes the design tokens, injects
 * the per-restaurant `--brand-*` CSS variables, AND exposes the
 * restaurant object via React context for descendant client
 * components to consume via `useRestaurant()`.
 *
 * Rules in `app/order/theme.css` are all scoped under `.order-flow` so
 * they never collide with the owner-side globals.
 */
export function ThemeProvider({ restaurant, className, children }: ThemeProviderProps) {
  const brandPrimary = safeColor(restaurant.brandPrimary, FALLBACK_PRIMARY)
  const brandPrimaryHover = safeColor(restaurant.brandPrimaryHover, FALLBACK_PRIMARY_HOVER)
  const brandPrimaryFg = safeColor(restaurant.brandPrimaryFg, FALLBACK_PRIMARY_FG)
  const brandSecondary = safeColor(restaurant.brandSecondary, FALLBACK_SECONDARY)

  // Re-create the context value only when the restaurant actually
  // changes — prevents needless re-renders down the tree.
  const value = useMemo(() => restaurant, [restaurant])

  const style = {
    '--brand-primary': brandPrimary,
    '--brand-primary-hover': brandPrimaryHover,
    '--brand-primary-fg': brandPrimaryFg,
    '--brand-secondary': brandSecondary,
    ...(restaurant.brandLogoUrl
      ? { '--brand-logo-url': `url(${restaurant.brandLogoUrl})` }
      : {}),
  } as CSSProperties

  return (
    <RestaurantContext.Provider value={value}>
      <div className={cn('order-flow', className)} style={style}>
        {children}
      </div>
    </RestaurantContext.Provider>
  )
}

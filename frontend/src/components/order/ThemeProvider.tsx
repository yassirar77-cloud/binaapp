import type { CSSProperties, ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { RestaurantTheme } from './types'

/**
 * Hardcoded default for PR 1 — the foundation drop.
 *
 * TODO(restaurant): Replace with real subdomain resolution from middleware
 * (e.g. `pelita.binaapp.my` -> websites.slug='pelita') in PR 2 or whichever
 * PR first needs real restaurant data (likely PR 3 menu page).
 *
 * TODO(restaurant): Add brand_primary, brand_primary_hover, brand_primary_fg,
 * brand_secondary columns to the `websites` table — currently hardcoded.
 */
export const DEFAULT_RESTAURANT: RestaurantTheme = {
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

/**
 * Wraps the customer-flow tree, scopes the design tokens, and injects
 * the per-restaurant `--brand-*` CSS variables. Server component — no
 * client behavior, just structural styling.
 *
 * Rules in `app/order/theme.css` are all scoped under `.order-flow` so
 * they never collide with the owner-side globals.
 */
export function ThemeProvider({ restaurant, className, children }: ThemeProviderProps) {
  const brandPrimary = safeColor(restaurant.brandPrimary, FALLBACK_PRIMARY)
  const brandPrimaryHover = safeColor(restaurant.brandPrimaryHover, FALLBACK_PRIMARY_HOVER)
  const brandPrimaryFg = safeColor(restaurant.brandPrimaryFg, FALLBACK_PRIMARY_FG)
  const brandSecondary = safeColor(restaurant.brandSecondary, FALLBACK_SECONDARY)

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
    <div className={cn('order-flow', className)} style={style}>
      {children}
    </div>
  )
}

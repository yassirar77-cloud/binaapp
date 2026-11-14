'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

/**
 * Resolved restaurant data from the `?r=` subdomain query parameter.
 *
 * Persisted under `binaapp_restaurant` so a page refresh mid-flow doesn't
 * lose the restaurant context.  The identify page writes this store after
 * a successful `/api/v1/websites/by-domain/{subdomain}` call; every
 * downstream page (menu, cart, checkout, tracking) reads from it.
 *
 * Uses `skipHydration: true` to avoid Next.js SSR/client hydration
 * mismatches — the layout calls `useRestaurantStore.persist.rehydrate()`
 * inside a `useEffect` and renders a skeleton until hydration completes.
 */

export interface ResolvedRestaurant {
  id: string
  name: string
  businessName: string
  subdomain: string
  whatsappNumber: string | null
  status: string
}

/**
 * Dine-in context from a table QR code (`?meja=5` on the restaurant's
 * site, carried into `/order/identify?r=…&meja=5`).
 *
 * It is bound to one restaurant and expires: a customer who scanned a
 * table last week and orders from home today must land in the delivery
 * flow, not send food to a table they are not sitting at.
 */
export interface TableContext {
  number: string
  restaurantId: string
  /** ms since epoch when the QR was scanned. */
  setAt: number
}

/** One sitting. After this the table marker is ignored. */
export const TABLE_TTL_MS = 3 * 60 * 60 * 1000

/**
 * Table label as printed on the QR poster: letters, digits, dash; max 8.
 * Mirrors `normalize_table_number` on the backend, which is the one that
 * actually enforces it. Returns null for anything else.
 */
export function normalizeTableNumber(raw: string | null | undefined): string | null {
  const table = (raw || '').trim().toUpperCase()
  return /^[A-Z0-9-]{1,8}$/.test(table) ? table : null
}

/** The table to use right now for this restaurant, or null. */
export function activeTable(
  table: TableContext | null,
  restaurantId: string | null | undefined,
  now: number = Date.now()
): string | null {
  if (!table || !restaurantId) return null
  if (table.restaurantId !== restaurantId) return null
  if (now - table.setAt > TABLE_TTL_MS || now < table.setAt) return null
  return normalizeTableNumber(table.number)
}

interface RestaurantStoreState {
  restaurant: ResolvedRestaurant | null
  table: TableContext | null
  /** Save resolved restaurant data (called after by-domain lookup). */
  setRestaurant: (data: ResolvedRestaurant) => void
  /** Wipe stored restaurant (e.g. when navigating away from order flow). */
  clearRestaurant: () => void
  /** Enter dine-in mode for a restaurant (table QR scanned). */
  setTable: (number: string, restaurantId: string) => void
  /** Leave dine-in mode (arrived without a table QR, or switched to delivery). */
  clearTable: () => void
}

export const useRestaurantStore = create<RestaurantStoreState>()(
  persist(
    (set) => ({
      restaurant: null,
      table: null,
      setRestaurant: (data) => set({ restaurant: data }),
      clearRestaurant: () => set({ restaurant: null, table: null }),
      setTable: (number, restaurantId) =>
        set({ table: { number, restaurantId, setAt: Date.now() } }),
      clearTable: () => set({ table: null }),
    }),
    {
      name: 'binaapp_restaurant',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ restaurant: state.restaurant, table: state.table }),
      skipHydration: true,
    }
  )
)

/**
 * Active dine-in table for the restaurant currently being ordered from,
 * or null when the customer is in the normal delivery flow.
 */
export function useTable(): string | null {
  return useRestaurantStore((s) => activeTable(s.table, s.restaurant?.id))
}

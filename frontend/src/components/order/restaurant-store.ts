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

interface RestaurantStoreState {
  restaurant: ResolvedRestaurant | null
  /** Save resolved restaurant data (called after by-domain lookup). */
  setRestaurant: (data: ResolvedRestaurant) => void
  /** Wipe stored restaurant (e.g. when navigating away from order flow). */
  clearRestaurant: () => void
}

export const useRestaurantStore = create<RestaurantStoreState>()(
  persist(
    (set) => ({
      restaurant: null,
      setRestaurant: (data) => set({ restaurant: data }),
      clearRestaurant: () => set({ restaurant: null }),
    }),
    {
      name: 'binaapp_restaurant',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ restaurant: state.restaurant }),
      skipHydration: true,
    }
  )
)

'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { CartItem } from './types'

/**
 * Customer-side cart store.
 *
 * Persists to localStorage under key `binaapp_cart` — same key as the
 * design prototype's `menu-data.js`, so any state authored in the
 * Claude Design preview will hydrate cleanly in dev.
 *
 * The store also tracks `restaurantId` (the website UUID the cart
 * belongs to) so the menu page can detect "user switched restaurants
 * but still has a cart from the previous one" and clear it before
 * confusing the customer at checkout.
 *
 * v1: localStorage only (single-device).
 * Future (TODO[cart]): swap to a server-side cart keyed by phone number
 * for cross-device support — the persist middleware's `storage` option
 * is the only line that needs to change.
 */

interface CartState {
  items: CartItem[]
  /** Website UUID this cart belongs to. Null until first set on menu mount. */
  restaurantId: string | null
  /** Free-text instructions for the kitchen, persisted with the cart. */
  kitchenNotes: string
  /**
   * Voucher code the customer applied, or null. The store only remembers
   * the code: whether it is valid and what it is worth always comes from
   * the server (see promo.ts).
   */
  promoCode: string | null
  /** Customer chose to spend their loyalty points on this order. */
  redeemPoints: boolean

  /** Adds an item or merges qty if it already exists. */
  add: (item: Omit<CartItem, 'qty'>, qty?: number) => void
  /** Sets qty for an item. Removes the item when qty <= 0. */
  setQty: (id: string, qty: number) => void
  /** Removes an item entirely. */
  remove: (id: string) => void
  /**
   * Clears the cart and any cart-attached state. Called after order
   * placement (next PR) and by the cross-restaurant guard.
   */
  clear: () => void
  /** Bind the cart to a specific restaurant; called on menu page mount. */
  setRestaurantId: (id: string) => void
  setKitchenNotes: (notes: string) => void
  /** Remember a code the server has just confirmed as valid. */
  setPromoCode: (code: string) => void
  clearPromoCode: () => void
  setRedeemPoints: (on: boolean) => void
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      restaurantId: null,
      kitchenNotes: '',
      promoCode: null,
      redeemPoints: false,
      add: (item, qty = 1) =>
        set((state) => {
          const idx = state.items.findIndex((c) => c.id === item.id)
          if (idx >= 0) {
            const next = [...state.items]
            next[idx] = { ...next[idx], qty: next[idx].qty + qty }
            return { items: next }
          }
          return { items: [...state.items, { ...item, qty }] }
        }),
      setQty: (id, qty) =>
        set((state) => {
          if (qty <= 0) {
            return { items: state.items.filter((c) => c.id !== id) }
          }
          return {
            items: state.items.map((c) => (c.id === id ? { ...c, qty } : c)),
          }
        }),
      remove: (id) =>
        set((state) => ({ items: state.items.filter((c) => c.id !== id) })),
      clear: () =>
        set({
          items: [],
          restaurantId: null,
          kitchenNotes: '',
          promoCode: null,
          redeemPoints: false,
        }),
      setRestaurantId: (id) => set({ restaurantId: id }),
      setKitchenNotes: (notes) => set({ kitchenNotes: notes }),
      setPromoCode: (code) =>
        set({ promoCode: (code || '').replace(/[\s-]/g, '').toUpperCase() || null }),
      clearPromoCode: () => set({ promoCode: null }),
      setRedeemPoints: (on) => set({ redeemPoints: on }),
    }),
    {
      name: 'binaapp_cart',
      storage: createJSONStorage(() => localStorage),
      // Persist all cart-attached state. Methods are recreated on hydration.
      partialize: (state) => ({
        items: state.items,
        restaurantId: state.restaurantId,
        kitchenNotes: state.kitchenNotes,
        promoCode: state.promoCode,
        redeemPoints: state.redeemPoints,
      }),
    }
  )
)

/* ----- Plain selector functions ----------------------------------------- */

export const cartCount = (items: CartItem[]): number =>
  items.reduce((s, i) => s + i.qty, 0)

/** Subtotal = sum of items × price. Discounts come from the server quote. */
export const cartTotal = (items: CartItem[]): number =>
  items.reduce((s, i) => s + i.price * i.qty, 0)

/* ----- Hook helpers ------------------------------------------------------ */

export const useCartItems = () => useCartStore((s) => s.items)
export const useCartCount = () => useCartStore((s) => cartCount(s.items))
export const useCartTotal = () => useCartStore((s) => cartTotal(s.items))
export const useKitchenNotes = () => useCartStore((s) => s.kitchenNotes)
export const usePromoCode = () => useCartStore((s) => s.promoCode)

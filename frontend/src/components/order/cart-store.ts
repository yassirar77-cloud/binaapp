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

/**
 * Stub promo code for v1. Real promo system lands later.
 * TODO(promo): Build real promo code system with backend validation.
 */
const STUB_PROMO_CODE = 'BINAAPP10'
const STUB_PROMO_PERCENT = 0.1
const STUB_PROMO_MAX_DISCOUNT = 5

export interface PromoApplyResult {
  success: boolean
  message: string
}

interface CartState {
  items: CartItem[]
  /** Website UUID this cart belongs to. Null until first set on menu mount. */
  restaurantId: string | null
  /** Free-text instructions for the kitchen, persisted with the cart. */
  kitchenNotes: string
  /** Currently-applied promo code, or null. v1 only recognises BINAAPP10. */
  promoCode: string | null

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
  /** Validate + apply a promo code. Returns user-facing message either way. */
  applyPromoCode: (code: string) => PromoApplyResult
  clearPromoCode: () => void
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      restaurantId: null,
      kitchenNotes: '',
      promoCode: null,
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
        }),
      setRestaurantId: (id) => set({ restaurantId: id }),
      setKitchenNotes: (notes) => set({ kitchenNotes: notes }),
      applyPromoCode: (code) => {
        const normalized = (code || '').trim().toUpperCase()
        if (!normalized) {
          return { success: false, message: 'Sila masukkan kod promo' }
        }
        if (normalized !== STUB_PROMO_CODE) {
          return { success: false, message: 'Kod promo tidak sah' }
        }
        set({ promoCode: STUB_PROMO_CODE })
        return { success: true, message: 'Kod promo digunakan' }
      },
      clearPromoCode: () => set({ promoCode: null }),
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
      }),
    }
  )
)

/* ----- Plain selector functions ----------------------------------------- */

export const cartCount = (items: CartItem[]): number =>
  items.reduce((s, i) => s + i.qty, 0)

/** Subtotal = sum of items × price (NO discount applied). */
export const cartTotal = (items: CartItem[]): number =>
  items.reduce((s, i) => s + i.price * i.qty, 0)

/**
 * Discount in RM. v1 only honors BINAAPP10 (10% off, capped at RM 5).
 * Returns 0 when no promo is applied or the code is unrecognised.
 */
export function cartDiscount(items: CartItem[], promoCode: string | null): number {
  if (promoCode !== STUB_PROMO_CODE) return 0
  const subtotal = cartTotal(items)
  const raw = subtotal * STUB_PROMO_PERCENT
  return Math.min(raw, STUB_PROMO_MAX_DISCOUNT)
}

/**
 * Grand total = subtotal − discount.
 *
 * Delivery fee is NOT included here — it gets added on the checkout page
 * once the customer picks a delivery zone.
 */
export function cartGrandTotal(items: CartItem[], promoCode: string | null): number {
  return cartTotal(items) - cartDiscount(items, promoCode)
}

/* ----- Hook helpers ------------------------------------------------------ */

export const useCartItems = () => useCartStore((s) => s.items)
export const useCartCount = () => useCartStore((s) => cartCount(s.items))
export const useCartTotal = () => useCartStore((s) => cartTotal(s.items))
export const useCartDiscount = () =>
  useCartStore((s) => cartDiscount(s.items, s.promoCode))
export const useCartGrandTotal = () =>
  useCartStore((s) => cartGrandTotal(s.items, s.promoCode))
export const useKitchenNotes = () => useCartStore((s) => s.kitchenNotes)
export const usePromoCode = () => useCartStore((s) => s.promoCode)

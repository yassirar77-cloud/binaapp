'use client'

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { Customer } from './types'

/**
 * Customer identity store.
 *
 * Persisted under a SEPARATE localStorage key (`binaapp_customer`) from
 * the cart store (`binaapp_cart`) because cart and customer have
 * different lifecycles: the cart clears after order placement, the
 * customer record persists for repeat orders.
 *
 * v1: localStorage only (single-device).
 * Future (TODO[customer]): server-side session token for cross-device
 * customer recognition.
 */

interface CustomerState {
  customer: Customer | null
  /** Capture customer identity (typically called after a successful lookup). */
  setCustomer: (customer: Customer) => void
  /** Patch fields on the existing customer (no-op if no customer is set). */
  updateCustomer: (patch: Partial<Customer>) => void
  /** Wipe customer identity (e.g. "switch account" on a shared device). */
  clearCustomer: () => void
}

export const useCustomerStore = create<CustomerState>()(
  persist(
    (set) => ({
      customer: null,
      setCustomer: (customer) => set({ customer }),
      updateCustomer: (patch) =>
        set((state) =>
          state.customer ? { customer: { ...state.customer, ...patch } } : state
        ),
      clearCustomer: () => set({ customer: null }),
    }),
    {
      name: 'binaapp_customer',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ customer: state.customer }),
    }
  )
)

/* ----- Hook helpers ------------------------------------------------------ */

export const useCustomer = () => useCustomerStore((s) => s.customer)
export const useCustomerPhone = () => useCustomerStore((s) => s.customer?.phone ?? '')

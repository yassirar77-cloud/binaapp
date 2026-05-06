'use client'

import { Search } from 'lucide-react'
import type { MenuItem } from '../menu-types'
import { useCartItems } from '../cart-store'
import { EmptyState } from './EmptyState'
import { MenuCard } from './MenuCard'

interface MenuGridProps {
  items: MenuItem[]
  onOpen: (item: MenuItem) => void
  onAdd: (item: MenuItem) => void
  onSetQty: (item: MenuItem, qty: number) => void
  /** True when the grid is empty because of search/filter (vs. no menu data at all). */
  searchQuery?: string
}

/**
 * 2-col mobile / 3-col tablet grid of MenuCards. Reads cart qty per
 * item from the cart store so adding items updates the in-card stepper
 * immediately.
 */
export function MenuGrid({ items, onOpen, onAdd, onSetQty, searchQuery }: MenuGridProps) {
  const cartItems = useCartItems()

  if (items.length === 0) {
    if (searchQuery && searchQuery.trim().length > 0) {
      return (
        <div className="menu-grid">
          <div style={{ gridColumn: '1 / -1' }}>
            <EmptyState
              icon={Search}
              title="Tiada padanan"
              body={`Tiada makanan untuk “${searchQuery}”. Cuba kata kunci lain.`}
            />
          </div>
        </div>
      )
    }
    // The "restaurant has no menu" empty state is handled at page level
    // before this component renders, so this branch covers "category
    // has no items" — uncommon but possible.
    return (
      <div className="menu-grid">
        <div style={{ gridColumn: '1 / -1' }}>
          <EmptyState title="Tiada makanan dalam kategori ini" />
        </div>
      </div>
    )
  }

  return (
    <div className="menu-grid">
      {items.map((item) => {
        const inCart = cartItems.find((c) => c.id === item.id)
        return (
          <MenuCard
            key={item.id}
            item={item}
            cartQty={inCart?.qty ?? 0}
            onOpen={onOpen}
            onAdd={onAdd}
            onSetQty={onSetQty}
          />
        )
      })}
    </div>
  )
}

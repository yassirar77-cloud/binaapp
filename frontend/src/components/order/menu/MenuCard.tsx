'use client'

import { ImageOff, Plus } from 'lucide-react'
import type { KeyboardEvent, MouseEvent } from 'react'
import { cn } from '@/lib/utils'
import type { MenuItem } from '../menu-types'
import { QuantityStepper } from './QuantityStepper'

interface MenuCardProps {
  item: MenuItem
  /** Current cart qty for this item, or 0 if not in cart. */
  cartQty: number
  /** Open the item detail sheet. */
  onOpen: (item: MenuItem) => void
  /** Add 1 unit (used by the small +/Add button when not yet in cart). */
  onAdd: (item: MenuItem) => void
  /** Adjust qty (used by the in-card stepper once item is in cart). */
  onSetQty: (item: MenuItem, qty: number) => void
}

/**
 * Single menu item tile — square image on top, name + description in
 * the middle, price + add/stepper at the bottom. The whole card is the
 * trigger for the detail sheet; the in-card +/stepper controls stop
 * propagation so quantity changes don't also open the sheet.
 *
 * Renders a placeholder icon when the restaurant hasn't uploaded an
 * image. Uses plain `<img loading="lazy">` (per pre-locked decision
 * #6 — `next/image` requires domain config that isn't in scope).
 *
 * Card uses `role="button"` rather than a real `<button>` so nested
 * interactive controls (the +/stepper) don't violate HTML spec.
 *
 * TODO(menu): Replace plain <img> with next/image when image domains
 *             are configured in next.config.js.
 */
export function MenuCard({ item, cartQty, onOpen, onAdd, onSetQty }: MenuCardProps) {
  const isSold = !item.isAvailable

  const handleOpen = () => {
    if (isSold) return
    onOpen(item)
  }

  const handleKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (isSold) return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onOpen(item)
    }
  }

  const stop = (e: MouseEvent) => e.stopPropagation()

  return (
    <div
      role="button"
      tabIndex={isSold ? -1 : 0}
      aria-label={`Lihat ${item.name}`}
      aria-disabled={isSold || undefined}
      className={cn('menu-item', isSold && 'sold')}
      onClick={handleOpen}
      onKeyDown={handleKey}
    >
      <div className="menu-item-img">
        {item.image ? (
          // TODO(menu): switch to next/image once image domains are
          // configured in next.config.js.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.image} alt={item.name} loading="lazy" decoding="async" />
        ) : (
          <ImageOff size={28} aria-hidden="true" />
        )}
        {isSold && (
          <div className="sold-out-overlay" aria-label="Habis stok">
            <div className="badge">Habis stok</div>
          </div>
        )}
      </div>
      <div className="menu-item-body">
        <h3 className="menu-item-name">{item.name}</h3>
        {item.description && <p className="menu-item-desc">{item.description}</p>}
        <div className="menu-item-foot">
          <div className="menu-price">
            <span className="rm">RM</span>
            {item.price.toFixed(2)}
          </div>
          {!isSold &&
            (cartQty > 0 ? (
              <QuantityStepper
                qty={cartQty}
                onDecrement={() => onSetQty(item, cartQty - 1)}
                onIncrement={() => onSetQty(item, cartQty + 1)}
                min={0}
              />
            ) : (
              <button
                type="button"
                className="add-btn"
                onClick={(e) => {
                  stop(e)
                  onAdd(item)
                }}
                aria-label={`Tambah ${item.name}`}
              >
                <Plus size={12} strokeWidth={2.5} aria-hidden="true" />
                Tambah
              </button>
            ))}
        </div>
      </div>
    </div>
  )
}

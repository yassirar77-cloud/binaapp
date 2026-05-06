'use client'

import { ImageOff, Minus, Plus, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import type { CartItem } from '../types'
import { useCartStore } from '../cart-store'

interface CartItemRowProps {
  item: CartItem
}

/**
 * One row in the cart list. Thumbnail + name + (qty stepper, price)
 * + remove button.
 *
 * Decrementing past 1 hits the qty=0 branch in the cart store which
 * removes the row entirely. Per Q6 in the PR-4 prompt we surface a
 * "Item dipadam" toast in that case so the customer knows their tap
 * removed the item rather than just zeroing it.
 */
export function CartItemRow({ item }: CartItemRowProps) {
  const setQty = useCartStore((s) => s.setQty)
  const remove = useCartStore((s) => s.remove)

  const handleDec = () => {
    if (item.qty <= 1) {
      remove(item.id)
      toast('Item dipadam', { icon: '🗑️', duration: 2000 })
      return
    }
    setQty(item.id, item.qty - 1)
  }

  const handleInc = () => {
    setQty(item.id, item.qty + 1)
  }

  const handleRemove = () => {
    remove(item.id)
    toast('Item dipadam', { icon: '🗑️', duration: 2000 })
  }

  return (
    <div className="cart-row">
      <div className="cart-thumb">
        {item.img ? (
          // TODO(menu): switch to next/image once image domains configured.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.img} alt={item.name} loading="lazy" decoding="async" />
        ) : (
          <ImageOff size={20} aria-hidden="true" />
        )}
      </div>

      <div className="cart-info">
        <h3 className="nm">{item.name}</h3>
        <div className="cart-actions">
          <div className="qty-stepper">
            <button
              type="button"
              onClick={handleDec}
              aria-label={`Kurang ${item.name}`}
            >
              <Minus size={12} strokeWidth={2.5} aria-hidden="true" />
            </button>
            <span className="q">{item.qty}</span>
            <button
              type="button"
              onClick={handleInc}
              aria-label={`Tambah ${item.name}`}
            >
              <Plus size={12} strokeWidth={2.5} aria-hidden="true" />
            </button>
          </div>
          <span className="price">RM {(item.price * item.qty).toFixed(2)}</span>
        </div>
      </div>

      <button
        type="button"
        className="delete-btn"
        onClick={handleRemove}
        aria-label={`Buang ${item.name}`}
      >
        <Trash2 size={18} strokeWidth={1.6} aria-hidden="true" />
      </button>
    </div>
  )
}

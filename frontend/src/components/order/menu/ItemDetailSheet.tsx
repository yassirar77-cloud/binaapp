'use client'

import { ImageOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button, Sheet } from '../primitives'
import type { MenuItem } from '../menu-types'
import { QuantityStepper } from './QuantityStepper'

interface ItemDetailSheetProps {
  /** Null = sheet closed. */
  item: MenuItem | null
  onClose: () => void
  /** Caller adds the chosen qty to the cart and closes the sheet. */
  onAdd: (item: MenuItem, qty: number) => void
}

/**
 * Bottom-sheet variant of the item card. Hero image, name, full
 * description, qty stepper, sticky bottom button.
 *
 * Variants/customizations are intentionally NOT modeled in v1
 * (TODO(menu): Add variant/customization support when backend
 *  schema supports it). The sheet exists today as a richer view of
 * the same payload the card shows, plus a multi-qty add affordance.
 */
export function ItemDetailSheet({ item, onClose, onAdd }: ItemDetailSheetProps) {
  const [qty, setQty] = useState(1)

  // Reset qty whenever the sheet opens for a new item.
  useEffect(() => {
    if (item) setQty(1)
  }, [item])

  if (!item) {
    // Sheet is closed — render the wrapper anyway so its mount/unmount
    // animations stay attached if the caller transitions in/out.
    return <Sheet open={false} onClose={onClose} />
  }

  const total = item.price * qty

  return (
    <Sheet open={true} onClose={onClose} ariaLabel={item.name}>
      <div className="sheet-img">
        {item.image ? (
          // TODO(menu): switch to next/image once image domains are
          // configured in next.config.js.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.image} alt={item.name} loading="lazy" decoding="async" />
        ) : (
          <ImageOff size={36} aria-hidden="true" />
        )}
      </div>
      <div className="sheet-body">
        <h2>{item.name}</h2>
        {item.description && <p className="desc">{item.description}</p>}
      </div>
      <div className="sheet-foot">
        <QuantityStepper
          qty={qty}
          onDecrement={() => setQty((q) => Math.max(1, q - 1))}
          onIncrement={() => setQty((q) => q + 1)}
          size="sheet"
          min={1}
        />
        <Button onClick={() => onAdd(item, qty)}>
          Tambah · RM {total.toFixed(2)}
        </Button>
      </div>
    </Sheet>
  )
}

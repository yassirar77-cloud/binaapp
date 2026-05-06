'use client'

import { Minus, Plus } from 'lucide-react'

interface QuantityStepperProps {
  qty: number
  onDecrement: () => void
  onIncrement: () => void
  /** Lower bound. Decrement is disabled when qty <= min. */
  min?: number
  /** Visual size — `card` lives inside menu cards, `sheet` lives in the bottom sheet. */
  size?: 'card' | 'sheet'
}

/**
 * Pill-shaped +/- stepper. Two visual sizes:
 *   - `card`  → 28px tall, brand-primary fill (used in MenuCard footer)
 *   - `sheet` → 44px tall, neutral fill (used in ItemDetailSheet footer)
 */
export function QuantityStepper({
  qty,
  onDecrement,
  onIncrement,
  min = 1,
  size = 'card',
}: QuantityStepperProps) {
  const stop = (e: React.MouseEvent) => e.stopPropagation()
  const className = size === 'sheet' ? 'add-stepper-big' : 'qty-stepper'

  return (
    <div className={className} onClick={stop}>
      <button
        type="button"
        aria-label="Kurang"
        onClick={onDecrement}
        disabled={qty <= min}
      >
        <Minus size={size === 'sheet' ? 16 : 12} strokeWidth={2.5} />
      </button>
      <span className="q">{qty}</span>
      <button type="button" aria-label="Tambah" onClick={onIncrement}>
        <Plus size={size === 'sheet' ? 16 : 12} strokeWidth={2.5} />
      </button>
    </div>
  )
}

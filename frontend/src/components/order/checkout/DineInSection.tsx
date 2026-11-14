'use client'

import { UtensilsCrossed } from 'lucide-react'

interface DineInSectionProps {
  table: string
  onSwitchToDelivery: () => void
  step?: number
}

/**
 * Replaces the address + coverage sections when the customer arrived
 * from a table QR code. There is nothing to fill in — the table is the
 * destination — but the customer must be able to see which table the
 * kitchen will be told, and to leave dine-in mode if they are not
 * actually sitting there.
 */
export function DineInSection({ table, onSwitchToDelivery, step = 2 }: DineInSectionProps) {
  return (
    <div className="co-sec fade-up" style={{ animationDelay: '40ms' }}>
      <div className="co-sec-head">
        <h2>
          <span className="num done">{step}</span>
          Makan di kedai
        </h2>
      </div>

      <div className="dinein-card">
        <div className="ic-wrap" aria-hidden="true">
          <UtensilsCrossed size={18} strokeWidth={2} />
        </div>
        <div className="body">
          <div className="nm">Meja {table}</div>
          <div className="nt">Pesanan akan dihantar ke meja ini. Tiada caj penghantaran.</div>
        </div>
      </div>

      <button type="button" className="dinein-switch" onClick={onSwitchToDelivery}>
        Bukan di kedai? Tukar ke penghantaran
      </button>
    </div>
  )
}

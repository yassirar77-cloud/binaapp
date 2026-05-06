'use client'

import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { TrackedOrder, TrackedOrderItem } from '../tracking-api'

interface OrderDetailsAccordionProps {
  order: TrackedOrder
  items: TrackedOrderItem[]
}

/**
 * Collapsible "Butiran pesanan" accordion. Default closed.
 * Expanded shows: line items + totals + payment method + address.
 */
export function OrderDetailsAccordion({ order, items }: OrderDetailsAccordionProps) {
  const [open, setOpen] = useState(false)
  return (
    <div className="accordion">
      <button
        type="button"
        className={cn('acc-head', open && 'open')}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="ttl">
          Butiran pesanan
          <span className="ct">· {items.length} item</span>
        </span>
        <ChevronDown className="chev" size={14} strokeWidth={2} aria-hidden="true" />
      </button>

      {open && (
        <div className="acc-body fade-up">
          {items.map((it) => (
            <div key={it.id} className="det-row">
              <span className="nm">
                <span className="qty">{it.quantity}×</span>
                {it.name}
              </span>
              <span className="pr">RM {it.totalPrice.toFixed(2)}</span>
            </div>
          ))}

          <div
            className="det-row"
            style={{
              paddingTop: 10,
              marginTop: 6,
              borderTop: '1px solid var(--border-soft)',
              fontWeight: 500,
            }}
          >
            <span>Subjumlah</span>
            <span className="pr">RM {order.subtotal.toFixed(2)}</span>
          </div>
          {order.deliveryFee > 0 && (
            <div className="det-row">
              <span style={{ color: 'var(--fg-muted)' }}>Penghantaran</span>
              <span className="pr">RM {order.deliveryFee.toFixed(2)}</span>
            </div>
          )}
          <div
            className="det-row"
            style={{ fontWeight: 500, paddingTop: 4 }}
          >
            <span>Jumlah</span>
            <span className="pr">RM {order.totalAmount.toFixed(2)}</span>
          </div>

          <div className="det-meta">
            <div>
              <div className="lbl">Pembayaran</div>
              <div className="v">{paymentLabel(order.paymentMethod)}</div>
            </div>
            <div>
              <div className="lbl">Alamat</div>
              <div className="v">{order.deliveryAddress || '—'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function paymentLabel(method: string): string {
  switch (method) {
    case 'cod':
      return 'Tunai semasa hantar (COD)'
    case 'online':
      return 'Online banking (FPX)'
    case 'ewallet':
      return 'eWallet'
    default:
      return method || 'Tidak dinyatakan'
  }
}

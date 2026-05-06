'use client'

import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { CartItem } from '../types'

interface OrderSummaryAccordionProps {
  items: CartItem[]
  subtotal: number
  deliveryFee: number
  discount: number
  promoCode: string | null
  total: number
  step?: number
}

/**
 * Section 5 — collapsible order summary. The header always shows the
 * one-line summary (`{count} item · RM {total}`); tapping expands the
 * itemized breakdown plus subtotal / delivery / discount lines.
 *
 * Default collapsed per the PR-5 prompt's pre-locked decision #6.
 */
export function OrderSummaryAccordion({
  items,
  subtotal,
  deliveryFee,
  discount,
  promoCode,
  total,
  step = 5,
}: OrderSummaryAccordionProps) {
  const [open, setOpen] = useState(false)
  const itemCount = items.reduce((s, i) => s + i.qty, 0)

  return (
    <div className="co-sec fade-up" style={{ animationDelay: '160ms' }}>
      <button
        type="button"
        className={cn('summary-toggle', open && 'open')}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <h2 style={{
          fontSize: 13, fontWeight: 500, margin: 0,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span className="num">{step}</span>
          Ringkasan pesanan
        </h2>
        <span style={{
          display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 13, color: 'var(--fg-muted)',
        }}>
          {itemCount} item · RM {total.toFixed(2)}
          <ChevronDown
            className="chev"
            size={14}
            strokeWidth={2}
            aria-hidden="true"
          />
        </span>
      </button>

      {open && (
        <div className="summary-body fade-up">
          {items.map((c) => (
            <div key={c.id} className="ord-line">
              <span className="nm">
                <span className="qty">{c.qty}×</span>
                {c.name}
              </span>
              <span className="pr">RM {(c.price * c.qty).toFixed(2)}</span>
            </div>
          ))}
          <div style={{
            borderTop: '1px solid var(--border-soft)',
            marginTop: 8, paddingTop: 8,
          }}>
            <div className="ord-line">
              <span style={{ color: 'var(--fg-muted)' }}>Subjumlah</span>
              <span className="pr">RM {subtotal.toFixed(2)}</span>
            </div>
            <div className="ord-line">
              <span style={{ color: 'var(--fg-muted)' }}>Penghantaran</span>
              <span className="pr">
                {deliveryFee > 0 ? `RM ${deliveryFee.toFixed(2)}` : '—'}
              </span>
            </div>
            {discount > 0 && (
              <div className="ord-line">
                <span style={{ color: 'var(--ok)' }}>
                  Diskaun{promoCode ? ` (${promoCode})` : ''}
                </span>
                <span className="pr" style={{ color: 'var(--ok)' }}>
                  −RM {discount.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

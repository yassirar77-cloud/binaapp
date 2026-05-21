'use client'

import { Wallet } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { OrderPaymentMethod } from '../checkout-api'

interface PaymentMethodSectionProps {
  selected: OrderPaymentMethod
  onSelect: (method: OrderPaymentMethod) => void
  step?: number
}

/**
 * Section 4 — payment method.
 *
 * BinaApp does not process food-order payments. Customers pay the
 * restaurant directly: cash to the rider on delivery (COD), or by
 * scanning the merchant's own bank/DuitNow QR shown on the
 * merchant's restaurant site. Neither flow involves a BinaApp
 * payment gateway redirect from this checkout, so this section
 * shows COD as the single selectable option.
 */
export function PaymentMethodSection({
  selected,
  onSelect,
  step = 4,
}: PaymentMethodSectionProps) {
  return (
    <div className="co-sec fade-up" style={{ animationDelay: '120ms' }}>
      <div className="co-sec-head">
        <h2>
          <span className="num done">{step}</span>
          Kaedah pembayaran
        </h2>
      </div>

      <button
        type="button"
        className={cn('pay-radio', selected === 'cod' && 'active')}
        onClick={() => onSelect('cod')}
      >
        <div className="ic-wrap">
          <Wallet size={18} strokeWidth={2} aria-hidden="true" />
        </div>
        <div className="body">
          <div className="nm">Bayar tunai semasa hantar</div>
          <div className="nt">Sediakan duit pas — paling popular</div>
        </div>
        <div className="radio-circle" />
      </button>
    </div>
  )
}

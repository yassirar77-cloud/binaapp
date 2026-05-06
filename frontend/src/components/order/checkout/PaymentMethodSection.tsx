'use client'

import { CreditCard, Wallet } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { OrderPaymentMethod } from '../checkout-api'

interface PaymentMethodSectionProps {
  selected: OrderPaymentMethod
  onSelect: (method: OrderPaymentMethod) => void
  step?: number
}

/**
 * Section 4 — payment method radios. v1 ships with COD active and
 * Online (FPX/ToyyibPay) **disabled** because the backend POST /orders
 * endpoint does not yet call ToyyibPay's create_bill — selecting it
 * today would create an unpaid order with no payment gateway redirect.
 *
 * The Online radio is rendered (per design) with a clear "Akan datang"
 * pill so the customer understands the option exists but is on its way.
 *
 * TODO(payment): Wire ToyyibPay create_bill into POST /api/v1/delivery
 *                /orders so `payment_method: "online"` returns a
 *                payment_url, then flip `disabled` to false on the
 *                Online radio below.
 *
 * TODO(payment): Add eWallet (Touch n Go / Boost / GrabPay) and Card
 *                (Visa / Mastercard) payment methods in a future PR.
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

      <button
        type="button"
        className={cn('pay-radio', selected === 'online' && 'active')}
        onClick={() => undefined}
        disabled
        aria-disabled="true"
        title="Pembayaran online akan tersedia tidak lama lagi"
      >
        <div className="ic-wrap">
          <CreditCard size={18} strokeWidth={2} aria-hidden="true" />
        </div>
        <div className="body">
          <div className="nm">
            Online banking (FPX) <span className="soon-badge">Akan datang</span>
          </div>
          <div className="nt">Maybank, CIMB, Public Bank…</div>
        </div>
        <div className="radio-circle" />
      </button>
    </div>
  )
}

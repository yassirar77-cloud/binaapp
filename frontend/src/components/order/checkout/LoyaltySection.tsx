'use client'

import { Gift } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { LoyaltyQuote } from '../promo'

interface LoyaltySectionProps {
  loyalty: LoyaltyQuote
  redeem: boolean
  onRedeemChange: (on: boolean) => void
  step: number
}

/**
 * Loyalty points at checkout. Rendered only when the merchant has turned
 * the programme on.
 *
 * Shows the balance, what this order will earn, and — when the balance
 * covers at least one block — a switch to spend points. The numbers are
 * the server's (see promo.ts); this component does no arithmetic of its
 * own beyond formatting.
 */
export function LoyaltySection({ loyalty, redeem, onRedeemChange, step }: LoyaltySectionProps) {
  const canRedeem = loyalty.redeemablePoints > 0
  const shortBy = Math.max(0, loyalty.redeemPoints - loyalty.balance)

  return (
    <div className="co-sec fade-up" style={{ animationDelay: '140ms' }}>
      <div className="co-sec-head">
        <h2>
          <span className="num done">{step}</span>
          Mata ganjaran
        </h2>
        <span className="loyalty-balance">{loyalty.balance} mata</span>
      </div>

      {canRedeem ? (
        <button
          type="button"
          role="switch"
          aria-checked={redeem}
          className={cn('pay-radio', redeem && 'active')}
          onClick={() => onRedeemChange(!redeem)}
        >
          <div className="ic-wrap">
            <Gift size={18} strokeWidth={2} aria-hidden="true" />
          </div>
          <div className="body">
            <div className="nm">
              Guna {loyalty.redeemablePoints} mata · jimat RM {loyalty.redeemDiscount.toFixed(2)}
            </div>
            <div className="nt">
              {redeem ? 'Diskaun mata ditolak daripada jumlah' : 'Ketik untuk tebus mata anda'}
            </div>
          </div>
          <div className="radio-circle" />
        </button>
      ) : (
        <p className="loyalty-note">
          {loyalty.balance > 0
            ? `Kumpul ${shortBy} mata lagi untuk tebus RM ${loyalty.redeemValue.toFixed(2)}.`
            : `Setiap ${loyalty.redeemPoints} mata boleh ditebus RM ${loyalty.redeemValue.toFixed(2)}.`}
        </p>
      )}

      {loyalty.willEarn > 0 && (
        <p className="loyalty-note earn">
          Anda akan kumpul <b>+{loyalty.willEarn} mata</b> selepas pesanan ini selesai.
        </p>
      )}
    </div>
  )
}

'use client'

import {
  useCartDiscount,
  useCartGrandTotal,
  useCartTotal,
  usePromoCode,
} from '../cart-store'

/**
 * Summary block at the bottom of the cart sheet (above the checkout
 * CTA). Subtotal + deferred delivery line + (optional) discount line +
 * grand total.
 *
 * Delivery fee is intentionally NOT calculated here — the cart can't
 * know the customer's selected zone yet. The line shows "Akan dihitung
 * di checkout" so the customer isn't surprised by the fee on the next
 * page (PR 5).
 */
export function CartSummary() {
  const subtotal = useCartTotal()
  const discount = useCartDiscount()
  const total = useCartGrandTotal()
  const promoCode = usePromoCode()

  return (
    <div className="summary">
      <div className="sum-row">
        <span>Subjumlah</span>
        <span className="v">RM {subtotal.toFixed(2)}</span>
      </div>
      <div className="sum-row muted-fee">
        <span>Yuran penghantaran</span>
        <span className="v">Akan dihitung di checkout</span>
      </div>
      {discount > 0 && (
        <div className="sum-row discount">
          <span>Diskaun ({promoCode})</span>
          <span className="v">−RM {discount.toFixed(2)}</span>
        </div>
      )}
      <div className="sum-total">
        <span className="l">Jumlah</span>
        <span className="v">
          <span className="rm">RM</span>
          {total.toFixed(2)}
        </span>
      </div>
    </div>
  )
}

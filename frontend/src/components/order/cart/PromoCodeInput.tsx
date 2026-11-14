'use client'

import { Tag } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { Button, Input } from '../primitives'
import { cartTotal, useCartStore, usePromoCode } from '../cart-store'
import { useCustomerStore } from '../customer-store'
import {
  fetchPromoQuote,
  normalizePromoCode,
  PromoQuoteError,
  usePromoQuote,
} from '../promo'
import { useRestaurant } from '../ThemeProvider'

/**
 * Three visual states:
 *   1. collapsed  — "Tambah kod promo" pill (default when no code applied)
 *   2. expanded   — input + "Guna" button
 *   3. applied    — green-tinted card with code + remove link
 *
 * A code is only remembered after the server confirms it for this cart.
 * It is re-checked whenever the cart changes: if it stops qualifying
 * (say the subtotal drops under the voucher's minimum) the row says why
 * and the discount line disappears, so the cart never shows a discount
 * the order will not get.
 */
export function PromoCodeInput() {
  const restaurant = useRestaurant()
  const promoCode = usePromoCode()
  const setPromoCode = useCartStore((s) => s.setPromoCode)
  const clearPromoCode = useCartStore((s) => s.clearPromoCode)
  const subtotal = useCartStore((s) => cartTotal(s.items))
  const phone = useCustomerStore((s) => s.customer?.phone ?? '')
  const { quote, loading } = usePromoQuote()

  const [expanded, setExpanded] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [checking, setChecking] = useState(false)

  // ---- Applied state.
  if (promoCode) {
    const voucher = quote?.voucher
    const stale = !loading && !!voucher && !voucher.valid
    return (
      <div className={stale ? 'promo-row' : 'promo-row applied'}>
        <Tag className="ic" size={16} aria-hidden="true" />
        <span>
          <span className="b">{promoCode}</span>
          {loading && ' · Menyemak…'}
          {!loading && voucher?.valid && ` · ${voucher.summary}`}
          {stale && ` · ${voucher.message}`}
        </span>
        <button
          type="button"
          className="rmv"
          onClick={() => {
            clearPromoCode()
            setDraft('')
            setError(null)
            setExpanded(false)
            toast('Kod promo dipadam', { duration: 2000 })
          }}
        >
          Buang
        </button>
      </div>
    )
  }

  // ---- Collapsed state.
  if (!expanded) {
    return (
      <button
        type="button"
        className="promo-row"
        onClick={() => setExpanded(true)}
      >
        <Tag className="ic" size={16} aria-hidden="true" />
        <span>Tambah kod promo</span>
        <span className="cta">Guna</span>
      </button>
    )
  }

  // ---- Expanded input state.
  const handleApply = async () => {
    const code = normalizePromoCode(draft)
    if (!code || checking) return
    setChecking(true)
    setError(null)
    try {
      const result = await fetchPromoQuote({
        websiteId: restaurant.websiteId,
        subtotal,
        phone,
        voucherCode: code,
      })
      if (result.voucher?.valid) {
        setPromoCode(code)
        setDraft('')
        setExpanded(false)
        toast.success(result.voucher.message || 'Kod promo digunakan', { duration: 2200 })
      } else {
        setError(result.voucher?.message || 'Kod promo tidak sah')
      }
    } catch (err) {
      setError(
        err instanceof PromoQuoteError
          ? err.message
          : 'Tidak dapat menyemak kod. Sila cuba lagi.'
      )
    } finally {
      setChecking(false)
    }
  }

  return (
    <div>
      <div className="promo-form">
        <Input
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value)
            if (error) setError(null)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              void handleApply()
            }
          }}
          placeholder="Kod promo"
          autoFocus
          aria-label="Kod promo"
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
        />
        <Button
          size="pill"
          onClick={() => void handleApply()}
          disabled={checking || normalizePromoCode(draft).length === 0}
          className="btn-pill"
        >
          {checking ? 'Menyemak…' : 'Guna'}
        </Button>
      </div>
      {error && (
        <div className="promo-error" role="alert">
          {error}
        </div>
      )}
    </div>
  )
}

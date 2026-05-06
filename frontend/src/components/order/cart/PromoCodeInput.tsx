'use client'

import { Tag } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { Button, Input } from '../primitives'
import { useCartStore, usePromoCode } from '../cart-store'

/**
 * Three visual states:
 *   1. collapsed  — "Tambah kod promo" pill (default when no code applied)
 *   2. expanded   — input + "Guna" button
 *   3. applied    — green-tinted card with code + remove link
 *
 * Stub-only for v1 — the only valid code is BINAAPP10 (10% off, capped
 * at RM 5). Real validation lands later: see TODO(promo) in cart-store.
 */
export function PromoCodeInput() {
  const promoCode = usePromoCode()
  const applyPromoCode = useCartStore((s) => s.applyPromoCode)
  const clearPromoCode = useCartStore((s) => s.clearPromoCode)

  const [expanded, setExpanded] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)

  // ---- Applied state.
  if (promoCode) {
    return (
      <div className="promo-row applied">
        <Tag className="ic" size={16} aria-hidden="true" />
        <span>
          <span className="b">{promoCode}</span> · 10% diskaun (max RM 5)
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
  const handleApply = () => {
    const result = applyPromoCode(draft)
    if (result.success) {
      setDraft('')
      setError(null)
      setExpanded(false)
      toast.success(result.message, { duration: 2200 })
    } else {
      setError(result.message)
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
              handleApply()
            }
          }}
          placeholder="BINAAPP10"
          autoFocus
          aria-label="Kod promo"
          autoCapitalize="characters"
          autoCorrect="off"
          spellCheck={false}
        />
        <Button
          size="pill"
          onClick={handleApply}
          disabled={draft.trim().length === 0}
          className="btn-pill"
        >
          Guna
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

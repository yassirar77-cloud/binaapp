'use client'

import { AlertCircle, Check, Lock } from 'lucide-react'
import { Button } from '../primitives'

interface PlaceOrderCTAProps {
  total: number
  disabled: boolean
  loading: boolean
  error: string | null
  onPlace: () => void
}

/**
 * Sticky bottom CTA — "Buat pesanan · RM {total}". Shows the inline
 * place-order error (if any) above the button, and a small "Pembayaran
 * selamat · Dikuasakan oleh BinaApp" reassurance line below.
 */
export function PlaceOrderCTA({ total, disabled, loading, error, onPlace }: PlaceOrderCTAProps) {
  return (
    <div className="place-bar">
      {error && (
        <div className="place-error" role="alert">
          <AlertCircle size={14} aria-hidden="true" style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{error}</span>
        </div>
      )}
      <Button disabled={disabled || loading} loading={loading} onClick={onPlace}>
        Buat pesanan · RM {total.toFixed(2)}
        {!loading && (
          <Check size={16} strokeWidth={2} aria-hidden="true" />
        )}
      </Button>
      <div className="secure">
        <Lock size={11} strokeWidth={2} aria-hidden="true" />
        Pembayaran selamat · Dikuasakan oleh BinaApp
      </div>
    </div>
  )
}

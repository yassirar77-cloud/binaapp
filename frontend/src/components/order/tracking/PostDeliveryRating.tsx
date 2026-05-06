'use client'

import { Info, Star } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Button, Textarea } from '../primitives'

interface PostDeliveryRatingProps {
  /**
   * Whether the rating endpoint is wired today. v1: NO — backend
   * doesn't expose POST /api/v1/orders/{id}/rate yet, so the submit
   * button stays disabled and a "Akan datang" note shows underneath.
   */
  enabled?: boolean
}

/**
 * Rating + tip + comment block shown when the order is delivered.
 *
 * v1 ships UI-only. Submit is disabled because the backend rating
 * endpoint doesn't exist yet — see TODO(rating) in the orchestrator.
 * Customers can still tap the stars / pick a tip preset visually, the
 * choices just aren't persisted server-side.
 */
export function PostDeliveryRating({ enabled = false }: PostDeliveryRatingProps) {
  const [rating, setRating] = useState(0)
  const [tip, setTip] = useState<number | null>(null)
  const [comment, setComment] = useState('')

  const tipPresets = [2, 5, 10]

  return (
    <div className="rating-card fade-up">
      <h3>Beri maklum balas</h3>

      <div className="stars" role="radiogroup" aria-label="Penilaian">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            className={cn('star-btn', n <= rating && 'active')}
            onClick={() => setRating(n)}
            aria-checked={n === rating}
            role="radio"
            aria-label={`${n} bintang`}
          >
            <Star
              size={28}
              strokeWidth={1.6}
              fill={n <= rating ? 'currentColor' : 'none'}
              aria-hidden="true"
            />
          </button>
        ))}
      </div>

      <div className="eyebrow" style={{ marginBottom: 8 }}>Tip untuk rider (pilihan)</div>
      <div className="tip-row">
        {tipPresets.map((amount) => (
          <button
            key={amount}
            type="button"
            className={cn('tip-chip', tip === amount && 'active')}
            onClick={() => setTip(tip === amount ? null : amount)}
          >
            RM {amount}
          </button>
        ))}
      </div>

      <Textarea
        rows={3}
        placeholder="Komen anda… (pilihan)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        aria-label="Komen"
        style={{ marginBottom: 12 }}
      />

      <Button disabled={!enabled || rating === 0}>
        {enabled ? 'Hantar maklum balas' : 'Hantar maklum balas (akan datang)'}
      </Button>

      {!enabled && (
        <div className="rating-disabled-note">
          <Info size={14} aria-hidden="true" style={{ flexShrink: 0, marginTop: 1 }} />
          <span>
            Sistem penilaian akan tersedia tidak lama lagi. Terima kasih atas
            kesabaran anda!
          </span>
        </div>
      )}
    </div>
  )
}

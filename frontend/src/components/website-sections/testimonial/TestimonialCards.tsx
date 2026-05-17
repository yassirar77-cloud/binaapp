/**
 * TestimonialCards — 3-card grid with avatar, quote, and star rating.
 * Mobile: single column stack.
 */

import React from 'react'
import type { TestimonialCardsProps } from '@/types/recipe'

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <i
          key={star}
          className={`fa-star text-sm ${star <= rating ? 'fa-solid' : 'fa-regular'}`}
          style={{ color: star <= rating ? '#F59E0B' : 'var(--color-text-muted)' }}
        />
      ))}
    </div>
  )
}

export default function TestimonialCards({ heading, reviews }: TestimonialCardsProps) {
  return (
    <div>
      <h2
        className="text-3xl sm:text-4xl font-bold text-center mb-12"
        style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
      >
        {heading}
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {reviews.map((review, i) => (
          <div
            key={i}
            className="p-6 rounded-2xl"
            style={{
              backgroundColor: 'var(--color-surface)',
              boxShadow: 'var(--shadow)',
            }}
          >
            <StarRating rating={review.rating} />

            <p
              className="mt-4 text-base leading-relaxed italic"
              style={{ color: 'var(--color-text-muted)' }}
            >
              &ldquo;{review.text}&rdquo;
            </p>

            <div className="mt-6 flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white"
                style={{ backgroundColor: 'var(--color-primary)' }}
              >
                {review.avatar_fallback}
              </div>
              <span
                className="text-sm font-semibold"
                style={{ color: 'var(--color-text)' }}
              >
                {review.name}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

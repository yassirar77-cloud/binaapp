/**
 * HeroSplit — hero section with image on one side, text on the other.
 * Mobile: stacks vertically (text first, then image).
 */

import React from 'react'
import type { HeroSplitProps } from '@/types/recipe'

export default function HeroSplit({
  headline,
  subheadline,
  cta_text,
  cta_link,
  cta_secondary_text,
  cta_secondary_link,
  image_url,
  image_alt = '',
  image_position = 'right',
}: HeroSplitProps) {
  const textContent = (
    <div className="flex flex-col justify-center py-12 lg:py-20">
      <h1
        className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight"
        style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
      >
        {headline}
      </h1>
      <p
        className="mt-6 text-lg sm:text-xl leading-relaxed max-w-lg"
        style={{ color: 'var(--color-text-muted)' }}
      >
        {subheadline}
      </p>
      <div className="mt-8 flex flex-wrap gap-4">
        <a
          href={cta_link}
          className="inline-block bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200"
        >
          {cta_text}
        </a>
        {cta_secondary_text && cta_secondary_link && (
          <a
            href={cta_secondary_link}
            className="inline-block border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200"
          >
            {cta_secondary_text}
          </a>
        )}
      </div>
    </div>
  )

  const imageContent = image_url ? (
    <div className="flex items-center justify-center py-8 lg:py-0">
      <img
        src={image_url}
        alt={image_alt}
        className="w-full max-w-lg lg:max-w-none rounded-3xl object-cover shadow-lg"
        style={{ maxHeight: '550px', boxShadow: 'var(--shadow-lg)' }}
        loading="eager"
      />
    </div>
  ) : (
    <div
      className="flex items-center justify-center py-8 lg:py-0"
    >
      <div
        className="w-full max-w-lg lg:max-w-none rounded-3xl flex items-center justify-center"
        style={{
          height: '400px',
          background: `linear-gradient(135deg, var(--color-primary), var(--color-secondary))`,
        }}
      >
        <i className="fa-solid fa-utensils text-6xl text-white/30" />
      </div>
    </div>
  )

  return (
    <div
      className="min-h-[80vh] flex items-center"
      style={{ backgroundColor: 'var(--color-background)' }}
    >
      <div className="mx-auto w-full px-4 sm:px-6 lg:px-8" style={{ maxWidth: 'var(--max-width, 1280px)' }}>
        <div className={`grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16 items-center ${
          image_position === 'left' ? 'lg:[direction:rtl] lg:*:[direction:ltr]' : ''
        }`}>
          {image_position === 'left' ? (
            <>
              {imageContent}
              {textContent}
            </>
          ) : (
            <>
              {textContent}
              {imageContent}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * AboutStory — image + paragraphs side by side.
 * Mobile: image stacks above text.
 */

import React from 'react'
import type { AboutStoryProps } from '@/types/recipe'

export default function AboutStory({
  heading,
  paragraphs,
  image_url,
  image_alt = '',
  image_position = 'left',
}: AboutStoryProps) {
  const textBlock = (
    <div className="flex flex-col justify-center">
      <h2
        className="text-3xl sm:text-4xl font-bold"
        style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
      >
        {heading}
      </h2>
      <div className="mt-6 space-y-4">
        {paragraphs.map((p, i) => (
          <p
            key={i}
            className="text-base sm:text-lg leading-relaxed"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {p}
          </p>
        ))}
      </div>
    </div>
  )

  const imageBlock = image_url ? (
    <div className="flex items-center justify-center">
      <img
        src={image_url}
        alt={image_alt}
        className="w-full rounded-2xl object-cover"
        style={{ maxHeight: '450px', boxShadow: 'var(--shadow-lg)' }}
        loading="lazy"
      />
    </div>
  ) : null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
      {image_position === 'left' ? (
        <>
          {imageBlock}
          {textBlock}
        </>
      ) : (
        <>
          {textBlock}
          {imageBlock}
        </>
      )}
    </div>
  )
}

/**
 * GalleryMasonry — CSS columns masonry layout.
 * Mobile: 1 column. Tablet: 2 columns. Desktop: 3 columns.
 * Images have rounded corners and hover scale effect.
 */

import React from 'react'
import type { GalleryMasonryProps } from '@/types/recipe'

export default function GalleryMasonry({ heading, images }: GalleryMasonryProps) {
  return (
    <div>
      <h2
        className="text-3xl sm:text-4xl font-bold text-center mb-12"
        style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
      >
        {heading}
      </h2>

      <div
        className="gap-4"
        style={{
          columnCount: 1,
          columnGap: '1rem',
        }}
      >
        <style dangerouslySetInnerHTML={{ __html: `
          @media (min-width: 640px) { .masonry-grid { column-count: 2 !important; } }
          @media (min-width: 1024px) { .masonry-grid { column-count: 3 !important; } }
        `}} />
        <div className="masonry-grid" style={{ columnCount: 1, columnGap: '1rem' }}>
          {images.map((img, i) => (
            <div
              key={i}
              className="mb-4 break-inside-avoid overflow-hidden rounded-2xl group"
            >
              <img
                src={img.url}
                alt={img.alt}
                className="w-full object-cover transition-transform duration-300 group-hover:scale-105"
                loading="lazy"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

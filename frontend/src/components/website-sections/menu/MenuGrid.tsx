/**
 * MenuGrid — 3-column grid of menu item cards with images.
 * Mobile: single column. Tablet: 2 columns.
 * Handles missing images with gradient + icon fallback.
 */

import React from 'react'
import type { MenuGridProps } from '@/types/recipe'

export default function MenuGrid({ heading, subheading, items }: MenuGridProps) {
  return (
    <div>
      <div className="text-center mb-12">
        <h2
          className="text-3xl sm:text-4xl font-bold"
          style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
        >
          {heading}
        </h2>
        {subheading && (
          <p
            className="mt-3 text-lg"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {subheading}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {items.map((item, i) => (
          <div
            key={i}
            className="rounded-2xl overflow-hidden transition-shadow duration-200 hover:shadow-lg"
            style={{
              backgroundColor: 'var(--color-surface)',
              boxShadow: 'var(--shadow)',
            }}
          >
            {item.image_url ? (
              <div className="relative">
                <img
                  src={item.image_url}
                  alt={item.name}
                  className="w-full h-48 object-cover"
                  loading="lazy"
                />
                {item.badge && (
                  <span
                    className="absolute top-3 right-3 text-white text-xs font-bold px-3 py-1 rounded-full"
                    style={{ backgroundColor: 'var(--color-primary)' }}
                  >
                    {item.badge}
                  </span>
                )}
              </div>
            ) : (
              <div
                className="w-full h-48 flex items-center justify-center"
                style={{
                  background: `linear-gradient(135deg, var(--color-primary), var(--color-secondary))`,
                }}
              >
                <i className="fa-solid fa-bowl-food text-4xl text-white/40" />
                {item.badge && (
                  <span
                    className="absolute top-3 right-3 text-white text-xs font-bold px-3 py-1 rounded-full"
                    style={{ backgroundColor: 'var(--color-primary)' }}
                  >
                    {item.badge}
                  </span>
                )}
              </div>
            )}

            <div className="p-5">
              <div className="flex items-start justify-between gap-3">
                <h3
                  className="text-lg font-semibold"
                  style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
                >
                  {item.name}
                </h3>
                <span
                  className="text-sm font-bold whitespace-nowrap"
                  style={{ color: 'var(--color-primary)' }}
                >
                  {item.price}
                </span>
              </div>
              <p
                className="mt-2 text-sm leading-relaxed"
                style={{ color: 'var(--color-text-muted)' }}
              >
                {item.description}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

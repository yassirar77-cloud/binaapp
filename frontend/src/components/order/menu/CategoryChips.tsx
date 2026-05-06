'use client'

import { cn } from '@/lib/utils'
import type { MenuCategory } from '../menu-types'

interface CategoryChipsProps {
  categories: MenuCategory[]
  activeId: string
  onChange: (id: string) => void
}

/**
 * Horizontally-scrollable chip strip, sticky under the search row.
 * Accepts the synthetic `'all'` pseudo-category at index 0; the active
 * chip flips to fg-on-bg per the design.
 */
export function CategoryChips({ categories, activeId, onChange }: CategoryChipsProps) {
  return (
    <div className="cats-row no-scrollbar" role="tablist" aria-label="Kategori menu">
      {categories.map((c) => (
        <button
          key={c.id}
          type="button"
          role="tab"
          aria-selected={c.id === activeId}
          className={cn('cat-chip', c.id === activeId && 'active')}
          onClick={() => onChange(c.id)}
        >
          {c.name}
        </button>
      ))}
    </div>
  )
}

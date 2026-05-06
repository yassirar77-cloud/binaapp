'use client'

import { cn } from '@/lib/utils'
import { DISPUTE_CATEGORIES, type DisputeCategoryId } from '../dispute-api'

interface CategoryChipsGridProps {
  selected: DisputeCategoryId | null
  onSelect: (id: DisputeCategoryId) => void
}

/**
 * Single-select chips for the 8 dispute categories. Emoji + BM label
 * each. Selected chip gets brand-tinted border + bg.
 */
export function CategoryChipsGrid({ selected, onSelect }: CategoryChipsGridProps) {
  return (
    <div className="dp-sec">
      <h3>
        Apa masalahnya?<span className="req">*</span>
      </h3>
      <div className="chips" role="radiogroup" aria-label="Kategori masalah">
        {DISPUTE_CATEGORIES.map((c) => (
          <button
            key={c.id}
            type="button"
            role="radio"
            aria-checked={c.id === selected}
            className={cn('chip', c.id === selected && 'active')}
            onClick={() => onSelect(c.id)}
          >
            <span className="em" aria-hidden="true">{c.emoji}</span>
            <span>{c.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

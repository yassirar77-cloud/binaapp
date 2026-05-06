'use client'

import { Search } from 'lucide-react'

interface SearchBarProps {
  value: string
  onChange: (next: string) => void
  placeholder?: string
}

/**
 * Sticky search row sitting under the menu header. Filter button hidden
 * for v1 — see `TODO(menu): Implement filter sheet` in MenuPageClient.
 */
export function SearchBar({ value, onChange, placeholder = 'Cari makanan…' }: SearchBarProps) {
  return (
    <div className="search-row">
      <Search className="search-icon" size={16} aria-hidden="true" />
      <input
        type="search"
        className="search-input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Cari makanan"
      />
    </div>
  )
}

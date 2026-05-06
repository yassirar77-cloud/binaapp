'use client'

import type { LucideIcon } from 'lucide-react'
import { ChefHat } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '../primitives'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  body?: string
  /** Optional CTA — e.g. retry button on a fetch error. */
  cta?: { label: string; onClick: () => void } | null
  children?: ReactNode
}

/**
 * Full-bleed empty / error state used inside `.menu-grid`. Defaults to
 * the chef-hat icon (most common case is "restaurant has no menu yet").
 */
export function EmptyState({ icon: Icon = ChefHat, title, body, cta, children }: EmptyStateProps) {
  return (
    <div className="menu-empty" role="status">
      <div className="ic">
        <Icon size={28} strokeWidth={1.5} aria-hidden="true" />
      </div>
      <h2>{title}</h2>
      {body && <p>{body}</p>}
      {cta && (
        <div style={{ maxWidth: 220, margin: '0 auto' }}>
          <Button onClick={cta.onClick}>{cta.label}</Button>
        </div>
      )}
      {children}
    </div>
  )
}

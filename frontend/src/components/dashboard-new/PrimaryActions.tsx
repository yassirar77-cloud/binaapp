'use client'

import { ReactElement, ReactNode } from 'react'
import ActionCard from './ActionCard'

export interface ActionItem {
  /** Lucide icon element */
  icon: ReactNode
  /** Card title, e.g. "Urus Penghantaran" */
  title: string
  /** Description text */
  description: string
  /** Status meta */
  meta: {
    dotColor: string
    label: string
    pulse?: boolean
  }
  /** Accent hue for icon */
  hue: string
  /** Navigation target */
  href: string
  /** Featured card (volt glow) */
  featured?: boolean
}

interface PrimaryActionsProps {
  actions: ActionItem[]
}

export default function PrimaryActions({
  actions,
}: PrimaryActionsProps): ReactElement {
  return (
    <section className="mb-10">
      {/* Section header */}
      <div className="flex justify-between items-baseline mb-4">
        <h2 className="font-geist font-semibold text-lg text-white tracking-[-0.02em] m-0">
          Tindakan pantas
        </h2>
        <span className="font-geist-mono text-[11px] text-[#4A4A5C] tracking-[0.08em] uppercase">
          {actions.length} alatan
        </span>
      </div>

      {/* Action cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {actions.map((action) => (
          <ActionCard
            key={action.title}
            icon={action.icon}
            title={action.title}
            description={action.description}
            meta={action.meta}
            hue={action.hue}
            href={action.href}
            featured={action.featured}
          />
        ))}
      </div>
    </section>
  )
}

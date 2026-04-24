'use client'

import { ReactElement, ReactNode } from 'react'

export type StatVariant = 'default' | 'urgent' | 'featured' | 'progress'

interface StatCardProps {
  /** Eyebrow label, e.g. "Jualan Hari Ini" */
  label: string
  /** Main value, e.g. "RM 1,284" or ReactNode for composite values */
  value: ReactNode
  /** Change badge, e.g. { text: '+18%', color: '#C7FF3D' } */
  delta?: { text: string; color: string; icon?: 'up' | 'down' }
  /** Subtitle below value */
  subtitle?: ReactNode
  /** Footer content (sparkline, breakdown, links) */
  footer?: ReactNode
  /** Visual variant */
  variant?: StatVariant
  /** Pulsing dot next to label (for urgent items) */
  pulse?: boolean
  /** Eyebrow label color override */
  labelColor?: string
}

export default function StatCard({
  label,
  value,
  delta,
  subtitle,
  footer,
  variant = 'default',
  pulse = false,
  labelColor,
}: StatCardProps): ReactElement {
  const surfaceClass =
    variant === 'featured' ? 'dash-surface-featured' : 'dash-surface'

  return (
    <div className={`${surfaceClass} p-[22px] relative overflow-hidden`}>
      {/* Featured glow accent */}
      {variant === 'featured' && (
        <div
          className="absolute -top-10 -right-10 w-40 h-40 rounded-full pointer-events-none"
          style={{
            background:
              'radial-gradient(circle, rgba(199,255,61,0.18), transparent 70%)',
          }}
        />
      )}

      {/* Eyebrow label */}
      <div
        className="dash-eyebrow mb-3.5 relative flex items-center gap-1.5"
        style={labelColor ? { color: labelColor, fontWeight: 600 } : undefined}
      >
        {pulse && <PulseDot color="#FF5A5F" />}
        {label}
      </div>

      {/* Main value */}
      <div className="relative">
        <div
          className="font-geist font-bold tracking-[-0.04em] dash-tnum leading-none mb-2.5"
          style={{
            fontSize: variant === 'featured' ? 46 : 40,
            color: variant === 'featured' ? '#C7FF3D' : '#fff',
            textShadow:
              variant === 'featured'
                ? '0 0 40px rgba(199,255,61,0.35)'
                : undefined,
          }}
        >
          {value}
        </div>
      </div>

      {/* Delta badge */}
      {delta && (
        <div className="flex items-center gap-1.5 mb-4 relative">
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-geist-mono text-[11px] font-semibold"
            style={{
              background: `${delta.color}1F`,
              border: `1px solid ${delta.color}38`,
              color: delta.color,
            }}
          >
            {delta.icon === 'up' && <DeltaArrowUp />}
            {delta.icon === 'down' && <DeltaArrowDown />}
            {delta.text}
          </span>
        </div>
      )}

      {/* Subtitle */}
      {subtitle && (
        <div className="text-[13px] text-ink-300 tracking-[-0.005em] mb-4 relative">
          {subtitle}
        </div>
      )}

      {/* Footer */}
      {footer && (
        <div className="dash-divider pt-3 relative">{footer}</div>
      )}
    </div>
  )
}

/* ── Internal atoms ── */

function PulseDot({ color }: { color: string }): ReactElement {
  return (
    <span className="relative inline-block w-2 h-2">
      <span
        className="absolute inset-0 rounded-full animate-pulse-red"
        style={{ background: color }}
      />
      <span
        className="absolute inset-0 rounded-full"
        style={{ background: color }}
      />
    </span>
  )
}

function DeltaArrowUp(): ReactElement {
  return (
    <svg width={10} height={10} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 17 17 7M7 7h10v10" />
    </svg>
  )
}

function DeltaArrowDown(): ReactElement {
  return (
    <svg width={10} height={10} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 7 7 17M17 17H7V7" />
    </svg>
  )
}

import type { CSSProperties, ReactNode } from 'react'

export type PillTone = 'green' | 'amber' | 'gray' | 'purple' | 'red'

interface PillProps {
  tone?: PillTone
  children: ReactNode
  dot?: boolean
  style?: CSSProperties
}

const TONE_MAP: Record<PillTone, [string, string, string]> = {
  green: ['var(--pill-green-bg)', 'var(--pill-green-fg)', '#10b981'],
  amber: ['var(--pill-amber-bg)', 'var(--pill-amber-fg)', '#f59e0b'],
  gray: ['var(--pill-gray-bg)', 'var(--pill-gray-fg)', '#8a8e9c'],
  purple: ['var(--pill-purple-bg)', 'var(--pill-purple-fg)', '#8b5cf6'],
  red: ['var(--pill-red-bg)', 'var(--pill-red-fg)', '#ef4444'],
}

export function Pill({ tone = 'gray', children, dot = false, style }: PillProps) {
  const [bg, fg, dotColor] = TONE_MAP[tone]
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        background: bg,
        color: fg,
        fontSize: 11,
        lineHeight: 1,
        fontWeight: 500,
        padding: '3px 8px',
        borderRadius: 'var(--r-pill)',
        whiteSpace: 'nowrap',
        letterSpacing: 0,
        ...style,
      }}
    >
      {dot && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: dotColor,
            animation: tone === 'green' ? 'profilePulseDot 1.8s ease-in-out infinite' : 'none',
          }}
        />
      )}
      {children}
    </span>
  )
}

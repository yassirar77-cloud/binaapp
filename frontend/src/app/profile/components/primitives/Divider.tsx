import type { CSSProperties } from 'react'

interface DividerProps {
  vertical?: boolean
  style?: CSSProperties
}

export function Divider({ vertical = false, style }: DividerProps) {
  return (
    <div
      style={{
        width: vertical ? '0.5px' : '100%',
        height: vertical ? '100%' : '0.5px',
        background: 'var(--border)',
        ...style,
      }}
    />
  )
}

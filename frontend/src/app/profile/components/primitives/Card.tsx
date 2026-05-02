import type { CSSProperties, HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode
  warn?: boolean
  style?: CSSProperties
}

export function Card({ children, warn = false, style, ...rest }: CardProps) {
  const borderColor = warn ? 'var(--warn-border)' : 'var(--border)'
  const borderWidth = warn ? '1px' : '0.5px'
  return (
    <section
      style={{
        background: 'var(--card-bg)',
        border: `${borderWidth} solid ${borderColor}`,
        borderRadius: 'var(--r-card)',
        padding: 24,
        ...style,
      }}
      {...rest}
    >
      {children}
    </section>
  )
}

'use client'

import { useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'

interface GhostButtonProps {
  children: ReactNode
  onClick?: () => void
  style?: CSSProperties
  type?: 'button' | 'submit' | 'reset'
}

export function GhostButton({ children, onClick, style, type = 'button' }: GhostButtonProps) {
  const [hover, setHover] = useState(false)
  return (
    <button
      type={type}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: hover ? '#f4f5f7' : 'transparent',
        color: 'var(--ink-1)',
        border: '0.5px solid var(--border-strong)',
        fontFamily: 'inherit',
        fontSize: 13,
        fontWeight: 500,
        padding: '7px 12px',
        minHeight: 36,
        borderRadius: 'var(--r-input)',
        transition: 'background 120ms',
        cursor: 'pointer',
        letterSpacing: 'inherit',
        ...style,
      }}
    >
      {children}
    </button>
  )
}

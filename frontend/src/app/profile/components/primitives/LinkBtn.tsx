'use client'

import { useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'

interface LinkBtnProps {
  children: ReactNode
  onClick?: () => void
  style?: CSSProperties
  type?: 'button' | 'submit' | 'reset'
}

export function LinkBtn({ children, onClick, style, type = 'button' }: LinkBtnProps) {
  const [hover, setHover] = useState(false)
  return (
    <button
      type={type}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: 'none',
        border: 0,
        padding: 0,
        color: hover ? 'var(--orange)' : 'var(--ink-2)',
        fontFamily: 'inherit',
        fontSize: 13,
        fontWeight: 500,
        cursor: 'pointer',
        transition: 'color 120ms',
        letterSpacing: 'inherit',
        ...style,
      }}
    >
      {children}
    </button>
  )
}

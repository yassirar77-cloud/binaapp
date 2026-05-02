'use client'

import { useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'

interface PrimaryButtonProps {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  style?: CSSProperties
  type?: 'button' | 'submit' | 'reset'
}

export function PrimaryButton({
  children,
  onClick,
  disabled = false,
  style,
  type = 'button',
}: PrimaryButtonProps) {
  const [hover, setHover] = useState(false)
  const bg = disabled ? '#e6e7eb' : hover ? 'var(--orange-hover)' : 'var(--orange)'
  const fg = disabled ? '#8a8e9c' : '#ffffff'
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: bg,
        color: fg,
        border: 0,
        fontFamily: 'inherit',
        fontSize: 13,
        fontWeight: 500,
        padding: '8px 14px',
        minHeight: 36,
        borderRadius: 'var(--r-input)',
        transition: 'background 120ms cubic-bezier(.25,1,.5,1)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        letterSpacing: 'inherit',
        ...style,
      }}
    >
      {children}
    </button>
  )
}

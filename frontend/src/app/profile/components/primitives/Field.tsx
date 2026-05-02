'use client'

import { useState } from 'react'
import type { HTMLInputTypeAttribute } from 'react'

export type FieldDensity = 'comfortable' | 'compact'

interface FieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  type?: HTMLInputTypeAttribute
  placeholder?: string
  full?: boolean
  density?: FieldDensity
  disabled?: boolean
  autoComplete?: string
}

export function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  full = false,
  density = 'comfortable',
  disabled = false,
  autoComplete,
}: FieldProps) {
  const [focus, setFocus] = useState(false)
  const padY = density === 'compact' ? 8 : 10
  return (
    <label
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        gridColumn: full ? '1 / -1' : 'auto',
      }}
    >
      <span style={{ fontSize: 12, color: 'var(--ink-2)', fontWeight: 400 }}>{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete={autoComplete}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        style={{
          background: disabled ? '#f4f5f7' : '#fff',
          border: focus ? '1px solid var(--orange)' : '0.5px solid var(--border-strong)',
          boxShadow: focus ? '0 0 0 3px rgba(249,115,22,0.12)' : 'none',
          borderRadius: 'var(--r-input)',
          padding: `${padY}px 12px`,
          fontFamily: 'inherit',
          fontSize: 14,
          outline: 'none',
          transition: 'border-color 120ms, box-shadow 120ms',
          color: 'var(--ink-1)',
          width: '100%',
          letterSpacing: 'inherit',
        }}
      />
    </label>
  )
}

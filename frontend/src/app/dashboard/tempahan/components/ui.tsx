'use client'

/** Small shared pieces for the Tempahan dashboard (dark dashboard theme). */

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

export const inputClass =
  'w-full rounded-lg bg-white/[0.05] border border-white/[0.08] px-3 py-2 text-sm text-white ' +
  'placeholder:text-white/30 focus:outline-none focus:border-[#C7FF3D]/50 disabled:opacity-50'

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-white/60 mb-1.5">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-white/35 mt-1">{hint}</span>}
    </label>
  )
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${props.className || ''}`} />
}

type Variant = 'primary' | 'ghost' | 'danger'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-[#C7FF3D] text-black hover:bg-[#d4ff66]',
  ghost: 'bg-white/[0.06] text-white/80 border border-white/[0.08] hover:bg-white/[0.1]',
  danger: 'bg-[#FF5A5F]/10 text-[#FF9A9D] border border-[#FF5A5F]/30 hover:bg-[#FF5A5F]/20',
}

export function Button({
  variant = 'ghost',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      {...props}
      className={`rounded-full px-4 py-2 text-xs font-semibold transition disabled:opacity-40 disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
    />
  )
}

export function Notice({ tone, children }: { tone: 'error' | 'success' | 'info'; children: ReactNode }) {
  const tones = {
    error: 'border-[#FF5A5F]/30 bg-[#FF5A5F]/10 text-[#FF9A9D]',
    success: 'border-[#C7FF3D]/30 bg-[#C7FF3D]/10 text-[#C7FF3D]',
    info: 'border-white/[0.08] bg-white/[0.04] text-white/60',
  }
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`rounded-xl border px-4 py-3 text-[13px] ${tones[tone]}`}>
      {children}
    </div>
  )
}

export function errorText(err: unknown, fallback = 'Ralat berlaku. Sila cuba lagi.'): string {
  const message = (err as any)?.message
  return typeof message === 'string' && message && message !== '[object Object]' ? message : fallback
}

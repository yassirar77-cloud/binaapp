import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/utils'

export type PillTone = 'neutral' | 'ok' | 'warn' | 'err' | 'info' | 'brand'

export interface PillProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: PillTone
  /** Show a leading currentColor dot (used for status pills). */
  dot?: boolean
  children?: ReactNode
}

const toneClass: Record<PillTone, string> = {
  neutral: '',
  ok: 'pill-ok',
  warn: 'pill-warn',
  err: 'pill-err',
  info: 'pill-info',
  brand: 'pill-brand',
}

export function Pill({ tone = 'neutral', dot = false, className, children, ...rest }: PillProps) {
  return (
    <span className={cn('pill', toneClass[tone], className)} {...rest}>
      {dot && <span className="dot" aria-hidden="true" />}
      {children}
    </span>
  )
}

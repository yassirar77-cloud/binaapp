'use client'

import { cn } from '@/lib/utils'
import { ReactNode, HTMLAttributes } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  className?: string
  /** Adds a subtle hover lift — use for interactive cards. */
  interactive?: boolean
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const paddingMap = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

export function Card({
  children,
  className,
  interactive = false,
  padding = 'md',
  ...rest
}: CardProps) {
  return (
    <div
      className={cn(
        'bg-ink-800/60 rounded-2xl border border-ink-700/70 backdrop-blur-sm',
        'transition-all duration-200',
        paddingMap[padding],
        interactive &&
          'cursor-pointer hover:border-ink-600 hover:bg-ink-800 hover:-translate-y-0.5 hover:shadow-card',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('mb-4 flex items-start justify-between gap-4', className)}>{children}</div>
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h3 className={cn('text-base font-semibold text-ink-100', className)}>{children}</h3>
}

export function CardDescription({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('text-sm text-ink-400 mt-1', className)}>{children}</p>
}

/* ------------------------------------------------------------------ */
/* Legacy helpers — kept here so existing pages keep working.          */
/* New code should import from Button, Input, Modal, Badge directly.   */
/* ------------------------------------------------------------------ */

export function StatCard({
  icon,
  label,
  value,
  subValue,
  subColor = 'text-ink-400',
}: {
  icon: ReactNode
  label: string
  value: string | number
  subValue?: string
  subColor?: string
}) {
  return (
    <Card padding="md">
      <div className="flex items-start justify-between mb-3">
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500/10 text-brand-300 text-lg">
          {icon}
        </span>
      </div>
      <p className="text-sm text-ink-400 mb-1">{label}</p>
      <p className="text-2xl font-semibold text-ink-100 tracking-tight">{value}</p>
      {subValue && <p className={cn('text-xs mt-1', subColor)}>{subValue}</p>}
    </Card>
  )
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search…',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div className="relative">
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        strokeWidth={2}
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-ink-800 border border-ink-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-ink-100 placeholder-ink-500 transition-colors focus:outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30"
      />
    </div>
  )
}

export function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap active:scale-[0.97]',
        active
          ? 'bg-brand-500 text-white shadow-soft'
          : 'bg-ink-800 text-ink-300 border border-ink-700 hover:border-ink-600 hover:text-ink-100',
      )}
    >
      {label}
    </button>
  )
}

export function Badge({
  children,
  color = 'gray',
}: {
  children: ReactNode
  color?: 'green' | 'yellow' | 'red' | 'blue' | 'gray' | 'orange' | 'brand'
}) {
  const colors = {
    green: 'bg-ok-500/15 text-ok-400 ring-ok-500/20',
    yellow: 'bg-warn-500/15 text-warn-400 ring-warn-500/20',
    red: 'bg-err-500/15 text-err-400 ring-err-500/20',
    blue: 'bg-blue-500/15 text-blue-400 ring-blue-500/20',
    gray: 'bg-ink-700/60 text-ink-300 ring-ink-600/40',
    orange: 'bg-brand-orange/15 text-orange-400 ring-orange-500/20',
    brand: 'bg-brand-500/15 text-brand-300 ring-brand-500/30',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ring-1',
        colors[color],
      )}
    >
      {children}
    </span>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-16">
      <p className="text-ink-500 text-sm">{message}</p>
    </div>
  )
}

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-7 h-7 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

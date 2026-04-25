'use client'

import { cn } from '@/lib/utils'
import { ReactNode, HTMLAttributes } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  className?: string
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
        'bg-white rounded-2xl border border-ink-200/80 shadow-soft',
        'transition-all duration-200',
        paddingMap[padding],
        interactive &&
          'cursor-pointer hover:border-ink-300 hover:-translate-y-0.5 hover:shadow-card',
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
  return <h3 className={cn('text-base font-semibold text-ink-900 tracking-tight', className)}>{children}</h3>
}

export function CardDescription({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('text-sm text-ink-500 mt-1', className)}>{children}</p>
}

export function Badge({
  children,
  color = 'gray',
  className,
}: {
  children: ReactNode
  color?: 'green' | 'yellow' | 'red' | 'gray' | 'brand'
  className?: string
}) {
  const colors = {
    green: 'bg-ok-500/10 text-ok-500 ring-ok-500/20',
    yellow: 'bg-warn-500/10 text-warn-500 ring-warn-500/20',
    red: 'bg-err-500/10 text-err-500 ring-err-500/20',
    gray: 'bg-ink-100 text-ink-600 ring-ink-200',
    brand: 'bg-brand-50 text-brand-700 ring-brand-100',
  }
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium ring-1',
        colors[color],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <Card padding="lg" className="text-center py-16">
      <div className="mx-auto h-12 w-12 rounded-full bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center mb-4">
        <svg className="h-6 w-6 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-ink-900 tracking-tight">{title}</h3>
      {description && <p className="text-sm text-ink-500 mt-2 max-w-md mx-auto">{description}</p>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </Card>
  )
}

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center justify-center py-12', className)}>
      <div className="w-7 h-7 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

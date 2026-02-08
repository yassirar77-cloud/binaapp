'use client'

import { cn } from '@/lib/utils'
import { ReactNode } from 'react'

export function Card({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('bg-gray-900 rounded-2xl border border-gray-800 p-4', className)}>
      {children}
    </div>
  )
}

export function StatCard({
  icon,
  label,
  value,
  subValue,
  subColor = 'text-gray-400',
}: {
  icon: string
  label: string
  value: string | number
  subValue?: string
  subColor?: string
}) {
  return (
    <Card>
      <div className="flex items-start justify-between mb-2">
        <span className="text-2xl">{icon}</span>
      </div>
      <p className="text-sm text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
      {subValue && (
        <p className={cn('text-xs mt-1', subColor)}>{subValue}</p>
      )}
    </Card>
  )
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search...',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div className="relative">
      <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-gray-900 border border-gray-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-orange focus:ring-1 focus:ring-brand-orange"
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
        'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap',
        active
          ? 'bg-brand-orange text-white'
          : 'bg-gray-900 text-gray-400 border border-gray-800 hover:border-gray-700'
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
  color?: 'green' | 'yellow' | 'red' | 'blue' | 'gray' | 'orange'
}) {
  const colors = {
    green: 'bg-green-500/20 text-green-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    red: 'bg-red-500/20 text-red-400',
    blue: 'bg-blue-500/20 text-blue-400',
    gray: 'bg-gray-500/20 text-gray-400',
    orange: 'bg-orange-500/20 text-orange-400',
  }

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium', colors[color])}>
      {children}
    </span>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-12">
      <p className="text-gray-500 text-sm">{message}</p>
    </div>
  )
}

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-8 h-8 border-3 border-brand-orange border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

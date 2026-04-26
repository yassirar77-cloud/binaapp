'use client'

import { cn } from '@/lib/utils'
import { ButtonHTMLAttributes, ReactNode, forwardRef } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'subtle'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  fullWidth?: boolean
}

const base =
  'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-150 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-900 ' +
  'disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]'

const variants: Record<Variant, string> = {
  primary:
    'bg-brand-500 text-white shadow-soft hover:bg-brand-400 hover:shadow-lift focus-visible:ring-brand-400',
  secondary:
    'bg-ink-800 text-ink-100 border border-ink-700 hover:border-ink-600 hover:bg-ink-700 focus-visible:ring-ink-500',
  ghost:
    'bg-transparent text-ink-200 hover:bg-ink-800 focus-visible:ring-ink-600',
  subtle:
    'bg-brand-500/10 text-brand-300 hover:bg-brand-500/20 focus-visible:ring-brand-400',
  danger:
    'bg-err-500 text-white hover:bg-err-400 focus-visible:ring-err-400',
}

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    leftIcon,
    rightIcon,
    fullWidth,
    className,
    children,
    disabled,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        base,
        variants[variant],
        sizes[size],
        fullWidth && 'w-full',
        className,
      )}
      {...rest}
    >
      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        leftIcon
      )}
      {children}
      {!loading && rightIcon}
    </button>
  )
})

'use client'

import { cn } from '@/lib/utils'
import {
  InputHTMLAttributes,
  TextareaHTMLAttributes,
  SelectHTMLAttributes,
  forwardRef,
  ReactNode,
} from 'react'

const fieldBase =
  'block w-full rounded-xl border bg-ink-800 px-3.5 py-2.5 text-sm text-ink-100 ' +
  'placeholder-ink-500 transition-colors duration-150 ' +
  'focus:outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-500/30 ' +
  'disabled:opacity-50 disabled:cursor-not-allowed'

const fieldOk = 'border-ink-700 hover:border-ink-600'
const fieldErr = 'border-err-500/60 focus:border-err-400 focus:ring-err-500/30'

interface FieldWrapperProps {
  label?: string
  hint?: string
  error?: string
  required?: boolean
  children: ReactNode
  className?: string
}

export function Field({ label, hint, error, required, children, className }: FieldWrapperProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      {label && (
        <label className="text-xs font-medium text-ink-300">
          {label}
          {required && <span className="text-err-400 ml-0.5">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs text-err-400">{error}</p>
      ) : hint ? (
        <p className="text-xs text-ink-500">{hint}</p>
      ) : null}
    </div>
  )
}

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
  leftIcon?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, invalid, leftIcon, ...rest },
  ref,
) {
  if (leftIcon) {
    return (
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-500">
          {leftIcon}
        </span>
        <input
          ref={ref}
          className={cn(fieldBase, invalid ? fieldErr : fieldOk, 'pl-10', className)}
          {...rest}
        />
      </div>
    )
  }
  return (
    <input
      ref={ref}
      className={cn(fieldBase, invalid ? fieldErr : fieldOk, className)}
      {...rest}
    />
  )
})

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, invalid, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(fieldBase, invalid ? fieldErr : fieldOk, 'min-h-[88px] resize-y', className)}
      {...rest}
    />
  )
})

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, invalid, children, ...rest },
  ref,
) {
  return (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          fieldBase,
          invalid ? fieldErr : fieldOk,
          'appearance-none pr-10 bg-no-repeat',
          className,
        )}
        {...rest}
      >
        {children}
      </select>
      <svg
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-400"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    </div>
  )
})

'use client'

import { cn } from '@/lib/utils'
import { ReactNode, useEffect } from 'react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg'
  staticOverlay?: boolean
}

const sizes = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  staticOverlay = false,
}: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      aria-modal="true"
      role="dialog"
      onClick={(e) => {
        if (!staticOverlay && e.target === e.currentTarget) onClose()
      }}
    >
      <div className="absolute inset-0 bg-ink-900/50 backdrop-blur-md" />
      <div
        className={cn(
          'relative w-full bg-white rounded-2xl shadow-lift border border-ink-200/80',
          'animate-scale-in',
          sizes[size],
        )}
      >
        {(title || description) && (
          <div className="px-6 pt-6 pb-4 border-b border-ink-100">
            {title && (
              <h2 className="text-lg font-semibold text-ink-900 tracking-tight">{title}</h2>
            )}
            {description && (
              <p className="text-sm text-ink-500 mt-1">{description}</p>
            )}
          </div>
        )}
        <div className="px-6 py-5">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-ink-100 flex items-center justify-end gap-2">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

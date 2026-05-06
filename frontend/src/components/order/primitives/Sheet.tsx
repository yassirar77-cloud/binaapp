'use client'

import { useEffect } from 'react'
import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface SheetProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  open: boolean
  onClose: () => void
  /** Render the small drag-grip handle at the top. Default: true. */
  grip?: boolean
  /** Accessible label for the dialog. */
  ariaLabel?: string
  children?: ReactNode
}

/**
 * Bottom sheet on mobile, centered modal feel on desktop (capped at 420px).
 *
 * Closes on ESC and on backdrop click. Locks body scroll while open.
 * Used by the menu page (item detail) and effectively by the cart page.
 */
export function Sheet({
  open,
  onClose,
  grip = true,
  ariaLabel,
  className,
  children,
  ...rest
}: SheetProps) {
  useEffect(() => {
    if (!open) return

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)

    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <>
      <div
        className="sheet-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        className={cn('sheet', className)}
        {...rest}
      >
        {grip && <div className="sheet-grip" aria-hidden="true" />}
        {children}
      </div>
    </>
  )
}

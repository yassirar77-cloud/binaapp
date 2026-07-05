'use client'

import { cn } from '@/lib/utils'
import { X } from 'lucide-react'
import { ReactNode, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

const FOCUSABLE_SEL =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

const EXIT_MS = 200

export interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg'
  /** When false, ESC and backdrop-click do not close the modal. */
  dismissible?: boolean
  hideClose?: boolean
  /** Extra classes on the panel. */
  className?: string
}

const sizes = {
  sm: 'sm:max-w-md',
  md: 'sm:max-w-lg',
  lg: 'sm:max-w-2xl',
}

/**
 * Dark-theme modal for dashboard/admin surfaces.
 * Centered scale-in card on desktop, bottom sheet on mobile.
 * Portal + focus trap + ESC + backdrop-click + body scroll lock.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'sm',
  dismissible = true,
  hideClose = false,
  className,
}: ModalProps) {
  const [mounted, setMounted] = useState(false)
  // Keep rendering during the exit animation.
  const [present, setPresent] = useState(open)
  const [closing, setClosing] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const previousActive = useRef<HTMLElement | null>(null)

  useEffect(() => setMounted(true), [])

  useEffect(() => {
    if (open) {
      setPresent(true)
      setClosing(false)
      return
    }
    if (!present) return
    setClosing(true)
    const t = setTimeout(() => {
      setPresent(false)
      setClosing(false)
    }, EXIT_MS)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // ESC + focus trap + scroll lock while open
  useEffect(() => {
    if (!open) return

    previousActive.current = document.activeElement as HTMLElement | null
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const focusFirst = () => {
      const panel = panelRef.current
      if (!panel) return
      const focusables = panel.querySelectorAll<HTMLElement>(FOCUSABLE_SEL)
      const target =
        panel.querySelector<HTMLElement>('[data-autofocus]') || focusables[0] || panel
      target.focus()
    }
    // After the enter animation has begun
    const raf = requestAnimationFrame(focusFirst)

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && dismissible) {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab') return
      const panel = panelRef.current
      if (!panel) return
      const focusables = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE_SEL))
      if (focusables.length === 0) {
        e.preventDefault()
        return
      }
      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      const active = document.activeElement as HTMLElement | null
      if (e.shiftKey) {
        if (active === first || !panel.contains(active)) {
          e.preventDefault()
          last.focus()
        }
      } else if (active === last || !panel.contains(active)) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKey, true)

    return () => {
      document.removeEventListener('keydown', onKey, true)
      document.body.style.overflow = prevOverflow
      previousActive.current?.focus?.()
    }
  }, [open, dismissible, onClose])

  if (!mounted || !present) return null

  return createPortal(
    <div
      className={cn(
        'fixed inset-0 z-[1200] flex items-end justify-center sm:items-center sm:p-4',
        'bg-black/60 backdrop-blur-sm',
        closing ? 'animate-fade-out' : 'animate-fade-in',
      )}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onMouseDown={(e) => {
        if (dismissible && e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        className={cn(
          'relative flex w-full max-h-[90dvh] flex-col overflow-hidden',
          'bg-ink-800 ring-1 ring-white/[0.08] shadow-2xl shadow-black/50',
          'rounded-t-2xl sm:rounded-2xl',
          closing
            ? 'animate-sheet-out sm:animate-scale-out'
            : 'animate-sheet-in sm:animate-scale-in',
          sizes[size],
          className,
        )}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* Grabber (mobile bottom sheet affordance) */}
        <div className="flex justify-center pt-2.5 sm:hidden" aria-hidden="true">
          <div className="h-1 w-10 rounded-full bg-white/15" />
        </div>

        {(title || !hideClose) && (
          <div className="flex items-start gap-3 px-5 pt-4 sm:pt-5">
            <div className="min-w-0 flex-1">
              {title && (
                <h2 className="font-geist text-base font-semibold tracking-tight text-ink-050">
                  {title}
                </h2>
              )}
              {description && <p className="mt-1 text-sm text-ink-300">{description}</p>}
            </div>
            {!hideClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Tutup"
                className="-mr-1 -mt-1 rounded-lg p-1.5 text-ink-400 transition-colors hover:bg-white/[0.06] hover:text-ink-100"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        )}

        {children != null && (
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-sm text-ink-200">
            {children}
          </div>
        )}

        {footer && (
          <div className="flex flex-col-reverse gap-2 px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-1 sm:flex-row sm:justify-end sm:pb-5">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}

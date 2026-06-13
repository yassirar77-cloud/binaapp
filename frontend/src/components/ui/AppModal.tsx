'use client'

import { cn } from '@/lib/utils'
import { ReactNode, useEffect } from 'react'
import {
  X,
  Info,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
} from 'lucide-react'

/**
 * AppModal — the single blocking-dialog component for BinaApp.
 *
 * Dark-navy + lime dashboard design language (see dashboard-new/dashboard.css):
 *   surface #161623 / #101020, lime accent #C7FF3D (volt-400), radius 18px,
 *   backdrop blur. Uses only existing tailwind tokens — no new colours/fonts.
 *
 * Mobile-first: bottom sheet on phones, centered card on >= sm.
 */

export type AppModalVariant =
  | 'info'
  | 'success'
  | 'warning'
  | 'error'
  | 'limit-reached'

interface AppModalProps {
  open: boolean
  onClose: () => void
  variant?: AppModalVariant
  title?: string
  description?: ReactNode
  children?: ReactNode
  /** Primary action button label. Omit to hide. */
  primaryLabel?: string
  onPrimary?: () => void
  primaryLoading?: boolean
  /** Secondary action button label. Omit to hide. */
  secondaryLabel?: string
  onSecondary?: () => void
  /** Hide the X close control + disable backdrop / Esc dismissal. */
  staticOverlay?: boolean
  /** Constrain width. Defaults to md. */
  size?: 'sm' | 'md' | 'lg'
  /** Tone of the primary button. */
  primaryTone?: 'lime' | 'danger'
  /** Override the variant icon (keeps the variant's accent ring). */
  icon?: ReactNode
}

const sizes = {
  sm: 'sm:max-w-sm',
  md: 'sm:max-w-md',
  lg: 'sm:max-w-2xl',
}

const variantMeta: Record<
  AppModalVariant,
  { Icon: typeof Info; ring: string; text: string; glow: string }
> = {
  info: {
    Icon: Info,
    ring: 'bg-info-400/10 ring-info-400/20',
    text: 'text-info-400',
    glow: '',
  },
  success: {
    Icon: CheckCircle2,
    ring: 'bg-ok-400/10 ring-ok-400/20',
    text: 'text-ok-400',
    glow: '',
  },
  warning: {
    Icon: AlertTriangle,
    ring: 'bg-warn-400/10 ring-warn-400/20',
    text: 'text-warn-400',
    glow: '',
  },
  error: {
    Icon: XCircle,
    ring: 'bg-err-400/10 ring-err-400/20',
    text: 'text-err-400',
    glow: '',
  },
  'limit-reached': {
    Icon: Sparkles,
    ring: 'bg-volt-400/10 ring-volt-400/25',
    text: 'text-volt-400',
    glow: 'shadow-[0_0_0_1px_rgba(199,255,61,0.10)]',
  },
}

export function AppModal({
  open,
  onClose,
  variant = 'info',
  title,
  description,
  children,
  primaryLabel,
  onPrimary,
  primaryLoading = false,
  secondaryLabel,
  onSecondary,
  staticOverlay = false,
  size = 'md',
  primaryTone = 'lime',
  icon,
}: AppModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !staticOverlay) onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose, staticOverlay])

  if (!open) return null

  const meta = variantMeta[variant]
  const Icon = meta.Icon

  return (
    <div
      className="fixed inset-0 z-[1200] flex items-end justify-center sm:items-center p-0 sm:p-4 animate-fade-in"
      aria-modal="true"
      role="dialog"
      onClick={(e) => {
        if (!staticOverlay && e.target === e.currentTarget) onClose()
      }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-ink-950/70 backdrop-blur-md" />

      {/* Panel */}
      <div
        className={cn(
          'relative w-full bg-gradient-to-b from-[#161623] to-[#101020]',
          'border border-white/[0.08] text-white',
          'rounded-t-3xl sm:rounded-[18px]',
          'shadow-[0_-12px_40px_rgba(0,0,0,0.5)] sm:shadow-[0_20px_60px_rgba(0,0,0,0.6)]',
          'animate-slide-up sm:animate-scale-in',
          'max-h-[92vh] overflow-y-auto',
          meta.glow,
          sizes[size],
        )}
      >
        {/* Mobile grab handle */}
        <div className="sm:hidden flex justify-center pt-3">
          <span className="h-1 w-10 rounded-full bg-white/15" />
        </div>

        {/* Close (X) */}
        {!staticOverlay && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="absolute right-3 top-3 sm:right-4 sm:top-4 z-10 rounded-lg p-1.5 text-white/40 hover:text-white hover:bg-white/[0.06] transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        )}

        <div className="px-6 pt-5 pb-6">
          {/* Icon */}
          <div
            className={cn(
              'mx-auto sm:mx-0 mb-4 flex h-12 w-12 items-center justify-center rounded-2xl ring-1',
              meta.ring,
            )}
          >
            {icon ?? <Icon className={cn('h-6 w-6', meta.text)} />}
          </div>

          {title && (
            <h2 className="text-center sm:text-left text-lg font-semibold tracking-tight text-white">
              {title}
            </h2>
          )}
          {description && (
            <div className="mt-1.5 text-center sm:text-left text-sm leading-relaxed text-white/60">
              {description}
            </div>
          )}

          {children && <div className="mt-4">{children}</div>}

          {(primaryLabel || secondaryLabel) && (
            <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-2.5">
              {secondaryLabel && (
                <button
                  type="button"
                  onClick={onSecondary ?? onClose}
                  disabled={primaryLoading}
                  className="inline-flex h-11 items-center justify-center rounded-xl border border-white/[0.12] bg-white/[0.04] px-5 text-sm font-medium text-white/80 hover:bg-white/[0.08] hover:text-white transition-colors disabled:opacity-50"
                >
                  {secondaryLabel}
                </button>
              )}
              {primaryLabel && (
                <button
                  type="button"
                  onClick={onPrimary}
                  disabled={primaryLoading}
                  className={cn(
                    'inline-flex h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold transition-all active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed',
                    primaryTone === 'danger'
                      ? 'bg-err-500 text-white hover:bg-err-400'
                      : 'bg-volt-400 text-ink-900 hover:bg-volt-300',
                  )}
                >
                  {primaryLoading && (
                    <span className="inline-block h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
                  )}
                  {primaryLabel}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AppModal

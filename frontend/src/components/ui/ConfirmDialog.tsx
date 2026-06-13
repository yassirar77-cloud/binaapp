'use client'

import { ReactNode } from 'react'
import { AppModal, AppModalVariant } from './AppModal'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
  variant?: AppModalVariant
  /** Use danger tone for the confirm button (destructive actions). */
  destructive?: boolean
}

/**
 * ConfirmDialog — drop-in replacement for window.confirm(), built on AppModal.
 * Keeps the dark-navy + lime design language consistent across the app.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Teruskan',
  cancelLabel = 'Batal',
  onConfirm,
  onCancel,
  loading = false,
  variant,
  destructive = false,
}: ConfirmDialogProps) {
  return (
    <AppModal
      open={open}
      onClose={onCancel}
      variant={variant ?? (destructive ? 'warning' : 'info')}
      title={title}
      description={description}
      primaryLabel={confirmLabel}
      onPrimary={onConfirm}
      primaryLoading={loading}
      primaryTone={destructive ? 'danger' : 'lime'}
      secondaryLabel={cancelLabel}
      onSecondary={onCancel}
      size="sm"
    />
  )
}

export default ConfirmDialog

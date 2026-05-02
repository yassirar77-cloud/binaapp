'use client'

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { RiderForm, type RiderFormRider, type RiderFormWebsite } from './RiderForm'

type Mode = 'add' | 'edit'

interface RiderFormModalProps {
  open: boolean
  mode: Mode
  rider?: RiderFormRider
  websites: RiderFormWebsite[]
  initialWebsiteId: string | null
  onClose: () => void
  onSaved: () => void
  onDeleted: () => void
  onShowToast: (msg: string, tone: 'success' | 'error') => void
}

const FOCUSABLE_SEL =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function RiderFormModal({
  open,
  mode,
  rider,
  websites,
  initialWebsiteId,
  onClose,
  onSaved,
  onDeleted,
  onShowToast,
}: RiderFormModalProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const [mounted, setMounted] = useState(false)
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string | null>(initialWebsiteId)

  useEffect(() => setMounted(true), [])

  useEffect(() => {
    if (open) setSelectedWebsiteId(initialWebsiteId ?? websites[0]?.id ?? null)
  }, [open, initialWebsiteId, websites])

  useEffect(() => {
    if (!open) return
    const previousActive = document.activeElement as HTMLElement | null
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const t = setTimeout(() => {
      const root = dialogRef.current
      if (!root) return
      const focusables = root.querySelectorAll<HTMLElement>(FOCUSABLE_SEL)
      focusables[0]?.focus()
    }, 0)

    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key === 'Tab') {
        const root = dialogRef.current
        if (!root) return
        const focusables = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE_SEL))
        if (focusables.length === 0) return
        const first = focusables[0]
        const last = focusables[focusables.length - 1]
        const active = document.activeElement as HTMLElement | null
        if (e.shiftKey && active === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && active === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKey)
    return () => {
      clearTimeout(t)
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = prevOverflow
      previousActive?.focus?.()
    }
  }, [open, onClose])

  if (!open || !mounted) return null

  const title = mode === 'edit' ? 'Urus rider' : 'Tambah rider baru'
  const subtitle = mode === 'edit'
    ? rider?.name?.trim() || 'Rider tanpa nama'
    : 'Cipta akaun rider baru untuk pasukan penghantaran anda'

  return createPortal(
    <div
      className="profile-hub"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 17, 26, 0.4)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        zIndex: 100,
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="rider-form-modal-title"
        className="rider-form-modal"
        style={{
          background: 'var(--card-bg)',
          borderRadius: 12,
          width: '100%',
          maxWidth: 520,
          maxHeight: 'calc(100vh - 32px)',
          overflowY: 'auto',
          padding: '20px 22px 22px',
          boxShadow: '0 20px 60px rgba(15, 17, 26, 0.18)',
        }}
      >
        <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
          <div style={{ minWidth: 0 }}>
            <h2 id="rider-form-modal-title" style={{ fontSize: 16, fontWeight: 500, margin: 0, color: 'var(--ink-1)' }}>
              {title}
            </h2>
            <p style={{ fontSize: 13, color: 'var(--ink-3)', margin: '2px 0 0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {subtitle}
            </p>
          </div>
          <button
            type="button"
            aria-label="Tutup"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 0,
              cursor: 'pointer',
              fontSize: 20,
              lineHeight: 1,
              color: 'var(--ink-3)',
              padding: 4,
            }}
          >
            ×
          </button>
        </header>

        <RiderForm
          mode={mode}
          rider={rider}
          websites={websites}
          selectedWebsiteId={selectedWebsiteId}
          onWebsiteChange={setSelectedWebsiteId}
          onSuccess={(msg) => {
            onShowToast(msg, 'success')
            onSaved()
            onClose()
          }}
          onError={(msg) => onShowToast(msg, 'error')}
          onCancel={onClose}
          onDeleted={() => {
            onDeleted()
          }}
        />
      </div>

      <style jsx>{`
        @media (max-width: 520px) {
          .rider-form-modal {
            max-width: 100% !important;
            border-radius: 0 !important;
            min-height: 100vh;
            max-height: 100vh !important;
          }
        }
      `}</style>
    </div>,
    document.body,
  )
}

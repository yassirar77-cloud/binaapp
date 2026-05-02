'use client'

import { useEffect, useState } from 'react'
import { GhostButton } from '@/app/profile/components/primitives/GhostButton'
import { PrimaryButton } from '@/app/profile/components/primitives/PrimaryButton'
import type { DisputeResolutionType } from '@/types'
import { DisputeModalShell } from './DisputeModalShell'
import { RESOLUTION_OPTIONS } from './constants'
import { useDisputeMutations } from './useDisputeMutations'

interface ResolveDisputeModalProps {
  open: boolean
  disputeId: string | null
  disputeNumber?: string | null
  onClose: () => void
  onResolved: () => void
  onShowToast: (msg: string, tone: 'success' | 'error') => void
}

export function ResolveDisputeModal({
  open,
  disputeId,
  disputeNumber,
  onClose,
  onResolved,
  onShowToast,
}: ResolveDisputeModalProps) {
  const [selected, setSelected] = useState<DisputeResolutionType>('issue_resolved')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { resolveDispute, submitting } = useDisputeMutations()

  useEffect(() => {
    if (open) {
      setSelected('issue_resolved')
      setNotes('')
      setError(null)
    }
  }, [open])

  async function handleConfirm() {
    if (!disputeId) return
    setError(null)
    try {
      await resolveDispute(disputeId, selected, notes.trim())
      onShowToast('Aduan ditutup', 'success')
      onResolved()
      onClose()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Gagal tutup aduan'
      setError(msg)
      onShowToast(msg, 'error')
    }
  }

  const subtitle = disputeNumber ? `#${disputeNumber}` : undefined

  return (
    <DisputeModalShell open={open} onClose={onClose} title="Tutup aduan" subtitle={subtitle} maxWidth={480}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-2)', marginBottom: 8 }}>
            Sebab penutupan
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {RESOLUTION_OPTIONS.map((opt) => {
              const active = selected === opt.key
              return (
                <label
                  key={opt.key}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    padding: '10px 12px',
                    background: active ? '#fff5ed' : '#fff',
                    border: active ? '1px solid var(--orange)' : '0.5px solid var(--border-strong)',
                    boxShadow: active ? '0 0 0 3px rgba(249,115,22,0.10)' : 'none',
                    borderRadius: 'var(--r-input)',
                    cursor: 'pointer',
                    transition: 'background 120ms, border-color 120ms',
                  }}
                >
                  <input
                    type="radio"
                    name="resolve-reason"
                    value={opt.key}
                    checked={active}
                    onChange={() => setSelected(opt.key)}
                    style={{ marginTop: 3, accentColor: 'var(--orange)' }}
                  />
                  <span style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-1)' }}>
                      {opt.icon} {opt.label}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>{opt.desc}</span>
                  </span>
                </label>
              )
            })}
          </div>
        </div>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-2)' }}>
            Nota <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>(pilihan)</span>
          </span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Tambah konteks penyelesaian…"
            rows={3}
            style={{
              background: '#fff',
              border: '0.5px solid var(--border-strong)',
              borderRadius: 'var(--r-input)',
              padding: '10px 12px',
              fontFamily: 'inherit',
              fontSize: 14,
              resize: 'vertical',
              color: 'var(--ink-1)',
              letterSpacing: 'inherit',
              outline: 'none',
            }}
          />
        </label>

        {error && (
          <div
            role="alert"
            style={{
              fontSize: 13,
              color: 'var(--pill-red-fg)',
              background: 'var(--pill-red-bg)',
              padding: '8px 12px',
              borderRadius: 'var(--r-input)',
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <GhostButton onClick={onClose}>Batal</GhostButton>
          <PrimaryButton onClick={handleConfirm} disabled={submitting || !disputeId}>
            {submitting ? 'Menutup…' : 'Sahkan tutup'}
          </PrimaryButton>
        </div>
      </div>
    </DisputeModalShell>
  )
}

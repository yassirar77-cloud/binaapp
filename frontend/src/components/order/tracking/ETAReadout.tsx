'use client'

import {
  DINE_IN_STEPS,
  dineInStepIndex,
  isDeliveredStatus,
  statusToStepIndex,
  VISUAL_STEPS,
} from '../status-mapper'

interface ETAReadoutProps {
  status: string
  /** Backend `eta_minutes` from the tracking response. */
  etaMinutes: number | null
  /** Table number for a dine-in order; null/undefined for delivery. */
  table?: string | null
}

/**
 * Hero ETA block — eyebrow ("Anggaran tiba"), big number (e.g.
 * "~25 minit"), and the current-step status line below.
 *
 * For delivered orders we swap the big number for a celebration
 * ("Sampai 🎉") to mirror the design's terminal state.
 *
 * The ETA value comes straight from the backend's `eta_minutes`
 * field. We DON'T compute it client-side per status — that would
 * fight with whatever the restaurant's delivery_settings say.
 */
export function ETAReadout({ status, etaMinutes, table }: ETAReadoutProps) {
  const delivered = isDeliveredStatus(status)
  const cancelled = status === 'cancelled' || status === 'rejected'

  // Dine-in: there is no arrival to estimate. The hero names the table and
  // says, in words, where the kitchen is with the order.
  if (table) {
    const label = DINE_IN_STEPS[dineInStepIndex(status)]?.label ?? 'Diterima'
    return (
      <div className="tk-hero">
        <div className="eta-label">Makan di kedai · Meja {table}</div>
        <div className="eta-row">
          {cancelled ? (
            <span className="eta-time" style={{ color: 'var(--err)' }}>
              Dibatalkan
            </span>
          ) : (
            <span className="eta-time">{delivered ? 'Selesai 🎉' : label}</span>
          )}
        </div>
        {!delivered && !cancelled && (
          <div className="status-line">
            {status === 'ready'
              ? 'Pesanan anda sedang dihantar ke meja'
              : 'Kami akan hantar ke meja anda sebaik sahaja siap'}
          </div>
        )}
      </div>
    )
  }

  const stepIndex = statusToStepIndex(status)
  const stepLabel = VISUAL_STEPS[stepIndex]?.label ?? 'Diterima'

  return (
    <div className="tk-hero">
      <div className="eta-label">Anggaran tiba</div>
      <div className="eta-row">
        {delivered ? (
          <span className="eta-time">Sampai 🎉</span>
        ) : cancelled ? (
          <span className="eta-time" style={{ color: 'var(--err)' }}>
            Dibatalkan
          </span>
        ) : etaMinutes != null && etaMinutes > 0 ? (
          <span className="eta-time">
            ~<span className="num">{etaMinutes}</span> minit
          </span>
        ) : (
          <span className="eta-time">Sebentar lagi</span>
        )}
      </div>
      {!delivered && !cancelled && (
        <div className="status-line">
          <span className="now">{stepLabel}</span>
          {' '}· pesanan anda sedang diproses
        </div>
      )}
    </div>
  )
}

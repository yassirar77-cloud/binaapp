'use client'

import {
  isDeliveredStatus,
  statusToStepIndex,
  VISUAL_STEPS,
} from '../status-mapper'

interface ETAReadoutProps {
  status: string
  /** Backend `eta_minutes` from the tracking response. */
  etaMinutes: number | null
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
export function ETAReadout({ status, etaMinutes }: ETAReadoutProps) {
  const stepIndex = statusToStepIndex(status)
  const stepLabel = VISUAL_STEPS[stepIndex]?.label ?? 'Diterima'
  const delivered = isDeliveredStatus(status)
  const cancelled = status === 'cancelled' || status === 'rejected'

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

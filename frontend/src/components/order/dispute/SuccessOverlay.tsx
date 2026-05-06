'use client'

import { ShieldCheck } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Button } from '../primitives'

interface SuccessOverlayProps {
  disputeNumber: string
  orderNumber: string
}

/**
 * Full-page success state shown after the dispute submits.
 * Mirrors the design's "Aduan diterima" layout with the BM timeline.
 *
 * "Pantau status aduan" CTA tries to route to a future dispute-tracking
 * page that doesn't exist yet — TODO(disputes) flagged in the
 * orchestrator. For now both CTAs route back to /track.
 */
export function SuccessOverlay({ disputeNumber, orderNumber }: SuccessOverlayProps) {
  const router = useRouter()
  const trackOrderHref = `/order/${encodeURIComponent(orderNumber)}/track`

  return (
    <div className="success fade-up">
      <div className="ic-wrap">
        <ShieldCheck size={36} strokeWidth={2} aria-hidden="true" />
      </div>
      <h2>Aduan diterima</h2>
      <p>Restoran akan jawab dalam 24 jam. Kami akan hantar notifikasi bila ada update.</p>

      <div className="ticket">
        <span className="lbl">Tiket</span>
        #{disputeNumber}
      </div>

      <div className="timeline" role="list">
        <div className="tl-row" role="listitem">
          <div className="tl-dot" aria-hidden="true" />
          <div className="body">
            <div className="nm">Aduan diterima</div>
            <div className="nt">Baru sebentar tadi</div>
          </div>
        </div>
        <div className="tl-row" role="listitem">
          <div className="tl-dot muted" aria-hidden="true" />
          <div className="body">
            <div className="nm" style={{ color: 'var(--fg-2)' }}>Disemak oleh restoran</div>
            <div className="nt">Dalam 24 jam</div>
          </div>
        </div>
        <div className="tl-row" role="listitem">
          <div className="tl-dot muted" aria-hidden="true" />
          <div className="body">
            <div className="nm" style={{ color: 'var(--fg-2)' }}>Resolusi</div>
            <div className="nt">Bayaran balik / hantar semula</div>
          </div>
        </div>
      </div>

      <div className="actions" style={{ marginTop: 24 }}>
        {/*
          TODO(disputes): Build /order/[orderNumber]/dispute/[disputeNumber]
                          so customers can read the AI/owner reply thread.
                          For v1 we route both CTAs back to the order
                          tracking page since we don't have a dedicated
                          dispute-status view yet.
        */}
        <Button onClick={() => router.push(trackOrderHref)}>
          Kembali ke pesanan
        </Button>
      </div>
    </div>
  )
}

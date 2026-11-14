'use client'

import { Card } from './primitives/Card'
import { GhostButton } from './primitives/GhostButton'

interface ReferralCardProps {
  onOpen: () => void
}

/** Entry point to /referrals — the page existed but nothing linked to it. */
export function ReferralCard({ onOpen }: ReferralCardProps) {
  return (
    <Card>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ minWidth: 0, flex: '1 1 220px' }}>
          <h2 style={{ fontSize: 15, fontWeight: 500, letterSpacing: '-0.01em' }}>Jemput rakan</h2>
          <p style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 4, lineHeight: 1.5 }}>
            Kongsi link jemputan anda. Anda dan rakan masing-masing dapat RM5 BinaCredit
            selepas rakan mendaftar dan sahkan e-mel.
          </p>
        </div>
        <GhostButton onClick={onOpen}>Dapatkan link</GhostButton>
      </div>
    </Card>
  )
}

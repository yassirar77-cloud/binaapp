'use client'

import { Lock } from 'lucide-react'

import { RANGE_OPTIONS, maxDaysForTier, type RangeDays } from '../lib/analytics'

interface Props {
  value: RangeDays
  tier: string
  onChange: (days: RangeDays) => void
  /** Called with the locked range when the user taps a range above their plan */
  onLockedClick: (days: RangeDays) => void
}

/** 7 / 30 / 90 hari pills. Ranges above the merchant's plan show a lock
 *  and open the upgrade prompt instead of switching (the server clamps
 *  regardless — this is honest UI, not the enforcement). */
export default function RangePicker({ value, tier, onChange, onLockedClick }: Props) {
  const allowed = maxDaysForTier(tier)

  return (
    <div className="inline-flex items-center gap-0.5 rounded-full bg-white/[0.05] p-1">
      {RANGE_OPTIONS.map((days) => {
        const locked = days > allowed
        const active = value === days
        return (
          <button
            key={days}
            type="button"
            onClick={() => (locked ? onLockedClick(days) : onChange(days))}
            className={`relative inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              active
                ? 'bg-white/[0.1] text-white'
                : locked
                  ? 'text-white/30 hover:text-white/50'
                  : 'text-white/50 hover:text-white/80'
            }`}
          >
            {days} hari
            {locked && <Lock size={11} strokeWidth={2} />}
          </button>
        )
      })}
    </div>
  )
}

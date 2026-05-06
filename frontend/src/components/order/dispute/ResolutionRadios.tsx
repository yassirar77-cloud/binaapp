'use client'

import { cn } from '@/lib/utils'
import { DISPUTE_RESOLUTIONS, type DisputeResolutionId } from '../dispute-api'

interface ResolutionRadiosProps {
  selected: DisputeResolutionId | null
  onSelect: (id: DisputeResolutionId) => void
}

/**
 * "Apa yang anda harapkan?" — 4 single-select radio cards. The
 * customer's choice doesn't have a dedicated backend column today,
 * so the orchestrator appends it to the description before submit.
 *
 * TODO(disputes): Add a `customer_preferred_resolution` column on
 *                 ai_disputes once the resolution workflow grows a
 *                 structured customer-side preference field.
 */
export function ResolutionRadios({ selected, onSelect }: ResolutionRadiosProps) {
  return (
    <div className="dp-sec">
      <h3>
        Apa yang anda harapkan?<span className="req">*</span>
      </h3>
      <div role="radiogroup" aria-label="Resolusi yang dijangka">
        {DISPUTE_RESOLUTIONS.map((r) => (
          <button
            key={r.id}
            type="button"
            role="radio"
            aria-checked={r.id === selected}
            className={cn('res-radio', r.id === selected && 'active')}
            onClick={() => onSelect(r.id)}
          >
            <div className="body">
              <div className="nm">{r.label}</div>
              <div className="nt">{r.hint}</div>
            </div>
            <div className="radio-circle" aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  )
}

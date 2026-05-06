'use client'

import { Bike, Check, ChefHat, ClipboardCheck, Package } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  statusToStepIndex,
  VISUAL_STEPS,
  type VisualStepId,
} from '../status-mapper'

interface ProgressStepsProps {
  status: string
}

/**
 * Horizontal 5-step indicator. Maps the backend status to one of the
 * 5 visual steps via `statusToStepIndex`. Each step shows:
 *   - past steps        → solid brand-primary dot with check mark
 *   - current step      → solid brand-primary dot with the step icon,
 *                         pulsing animation
 *   - future steps      → muted gray dot with the step icon
 *
 * Only the FIRST FOUR step labels render the in-line connector bar
 * (the 5th is the destination so its bar would have nothing to connect
 * to) — this is enforced via CSS `:last-child .step-bar { display: none }`.
 */
export function ProgressSteps({ status }: ProgressStepsProps) {
  const activeIndex = statusToStepIndex(status)

  // The design only renders 4 steps in the prototype's hero strip
  // (received → preparing → ready → delivery). The fifth `delivered`
  // state replaces the entire hero with a celebration — see
  // ETAReadout. We follow the same convention.
  const steps = VISUAL_STEPS.slice(0, 4)

  return (
    <div className="steps" role="list">
      {steps.map((s, i) => {
        const done = i < activeIndex
        const active = i === activeIndex
        return (
          <div
            key={s.id}
            role="listitem"
            className={cn('step', done && 'done', active && 'active')}
          >
            <div className="step-dot">
              {done ? (
                <Check size={14} strokeWidth={2.6} aria-hidden="true" />
              ) : (
                <StepIcon id={s.id} />
              )}
            </div>
            <div className="step-bar" aria-hidden="true" />
            <div className="step-label">{s.label}</div>
          </div>
        )
      })}
    </div>
  )
}

function StepIcon({ id }: { id: VisualStepId }) {
  switch (id) {
    case 'received':
      return <ClipboardCheck size={16} strokeWidth={2} aria-hidden="true" />
    case 'preparing':
      return <ChefHat size={16} strokeWidth={2} aria-hidden="true" />
    case 'ready':
      return <Package size={16} strokeWidth={2} aria-hidden="true" />
    case 'delivery':
      return <Bike size={16} strokeWidth={2} aria-hidden="true" />
    case 'delivered':
      return <Check size={16} strokeWidth={2.6} aria-hidden="true" />
  }
}

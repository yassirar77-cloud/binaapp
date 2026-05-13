'use client';

// 6-step horizontal timeline. Each step is marked completed when the current
// order status appears in its `matches` array (see TIMELINE_STEPS).
//
// Timestamps: the backend only exposes `created_at` and `confirmed_at` today,
// so we render those under steps 1 and 2 respectively and leave later steps
// label-only. When ready_at / picked_up_at land on the API, plug them in here
// without changing the layout.

import { Fragment } from 'react';
import { Check } from 'lucide-react';
import type { Order, OrderStatus } from '../lib/types';
import { TIMELINE_STEPS } from '../lib/constants';

interface Props {
  order: Order;
}

const LIME = '#C7FF3D';

function formatHM(iso: string | null): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString('ms-MY', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export default function Timeline({ order }: Props) {
  const status = order.status as OrderStatus;

  return (
    <div className="flex items-start w-full">
      {TIMELINE_STEPS.map((step, i) => {
        const done = (step.matches as ReadonlyArray<string>).includes(status);
        const nextStep = TIMELINE_STEPS[i + 1];
        const nextDone = nextStep
          ? (nextStep.matches as ReadonlyArray<string>).includes(status)
          : false;

        const stamp =
          step.key === 'pending'
            ? formatHM(order.created_at)
            : step.key === 'confirmed'
              ? formatHM(order.confirmed_at)
              : '';

        return (
          <Fragment key={step.key}>
            <div className="flex flex-col items-center min-w-0 shrink-0 basis-0 flex-1">
              <div
                className="flex items-center justify-center w-5 h-5 rounded-full transition-colors"
                style={
                  done
                    ? { backgroundColor: LIME, color: '#0B0B15' }
                    : {
                        backgroundColor: 'transparent',
                        boxShadow: 'inset 0 0 0 1.5px rgba(255,255,255,0.18)',
                        color: 'rgba(255,255,255,0.3)',
                      }
                }
              >
                {done ? (
                  <Check size={11} strokeWidth={3} />
                ) : (
                  <span className="block w-1.5 h-1.5 rounded-full bg-white/30" />
                )}
              </div>
              <span
                className={`mt-1.5 text-[10px] font-geist tracking-wide truncate max-w-full ${
                  done ? 'text-white/80' : 'text-white/35'
                }`}
              >
                {step.label}
              </span>
              {stamp ? (
                <span className="font-mono text-[9px] text-white/35 mt-0.5">
                  {stamp}
                </span>
              ) : null}
            </div>
            {i < TIMELINE_STEPS.length - 1 ? (
              <div
                className="h-px shrink grow-0 mt-2.5"
                style={{
                  flexBasis: 12,
                  backgroundColor: done && nextDone ? LIME : 'rgba(255,255,255,0.1)',
                }}
              />
            ) : null}
          </Fragment>
        );
      })}
    </div>
  );
}

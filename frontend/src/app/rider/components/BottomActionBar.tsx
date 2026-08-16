'use client';

// BottomActionBar — sticky CTA at the bottom of the detail screen.
// Label + next status come from ACTION_LABELS (shared with OrderRow's
// action pill); only the icon mapping lives here. For `delivering` + COD
// orders the parent intercepts the click to open CODModal (Phase 8); the
// bar itself doesn't know about the modal.

import {
  CheckCircle,
  Loader2,
  ShoppingBag,
  Truck,
} from 'lucide-react';

import { ACTION_LABELS } from '../lib/constants';
import type { OrderStatus, RiderOrder } from '../lib/types';

interface BottomActionBarProps {
  order: RiderOrder;
  pending: boolean;
  onAdvance: (order: RiderOrder, next: OrderStatus) => void;
}

// Icon per actionable status — labels stay in constants.ts.
const CTA_ICONS: Partial<Record<OrderStatus, typeof ShoppingBag>> = {
  ready: ShoppingBag,
  picked_up: Truck,
  delivering: CheckCircle,
};

export default function BottomActionBar({
  order,
  pending,
  onAdvance,
}: BottomActionBarProps) {
  const cta = ACTION_LABELS[order.status] ?? null;

  // Terminal / non-actionable states: show a passive message so the bar
  // still anchors the screen visually but the rider can't accidentally
  // re-trigger a transition.
  if (!cta) {
    const isDone =
      order.status === 'delivered' || order.status === 'completed';
    return (
      <div className="fixed bottom-0 left-0 right-0 z-30 bg-[var(--rider-bg)]/95 backdrop-blur-md border-t border-[var(--rider-border)] rider-safe-pb">
        <div className="px-4 pt-3 pb-3">
          <p className="h-14 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] flex items-center justify-center text-[14px] text-[var(--rider-text-2)]">
            {isDone ? 'Selesai. Terima kasih.' : 'Tiada tindakan untuk status ini.'}
          </p>
        </div>
      </div>
    );
  }

  const { label, nextStatus } = cta;
  const Icon = CTA_ICONS[order.status] ?? CheckCircle;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 bg-[var(--rider-bg)]/95 backdrop-blur-md border-t border-[var(--rider-border)] rider-safe-pb">
      <div className="px-4 pt-3 pb-3">
        <button
          type="button"
          onClick={() => onAdvance(order, nextStatus)}
          disabled={pending}
          className="w-full h-14 rounded-2xl bg-[var(--rider-lime)] hover:bg-[var(--rider-lime-2)] text-black font-semibold text-base flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {pending ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Icon className="w-5 h-5" strokeWidth={2.25} />
          )}
          {label}
        </button>
      </div>
    </div>
  );
}

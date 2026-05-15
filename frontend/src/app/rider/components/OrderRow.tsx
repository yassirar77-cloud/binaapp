'use client';

// OrderRow — single card in the orders list. Tap the body to open the
// detail screen; the inline action button (when present) advances the
// state machine without leaving the list.

import { ChevronRight, Loader2, MapPin } from 'lucide-react';

import { ACTION_LABELS, STATUS_META } from '../lib/constants';
import { relTime } from '../lib/relTime';
import type { OrderStatus, RiderOrder } from '../lib/types';

interface OrderRowProps {
  order: RiderOrder;
  pending?: boolean;
  onOpen: (order: RiderOrder) => void;
  onAdvance: (order: RiderOrder, next: OrderStatus) => void;
}

export default function OrderRow({
  order,
  pending,
  onOpen,
  onAdvance,
}: OrderRowProps) {
  const meta = STATUS_META[order.status];
  const action = ACTION_LABELS[order.status];

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={() => onOpen(order)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen(order);
        }
      }}
      className="mx-4 mt-2.5 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] hover:border-[var(--rider-border-2)] p-3.5 flex items-center gap-3 cursor-pointer transition-colors"
    >
      {/* Status dot */}
      <span
        className="w-2 h-2 rounded-full shrink-0 mt-1.5 self-start"
        style={{ backgroundColor: meta?.color ?? '#86869A' }}
        aria-hidden
      />

      {/* Body */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 text-[var(--rider-muted)]">
          <span className="font-mono text-[11px]">#{order.order_number}</span>
          <span>·</span>
          <span className="text-[11px]">{relTime(order.created_at)}</span>
        </div>
        <p className="mt-0.5 text-[14px] font-semibold text-white truncate">
          {order.customer_name}
        </p>
        <p className="mt-0.5 flex items-center gap-1 text-[12px] text-[var(--rider-text-2)] truncate">
          <MapPin className="w-3 h-3 shrink-0" />
          <span className="truncate">{order.delivery_address}</span>
        </p>
      </div>

      {/* Right column */}
      <div className="shrink-0 flex flex-col items-end gap-1.5">
        <p className="font-mono text-[14px] font-semibold text-[var(--rider-lime)]">
          RM{order.total}
        </p>
        {action ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onAdvance(order, action.nextStatus);
            }}
            disabled={pending}
            className="h-8 px-3 rounded-full bg-[var(--rider-lime)] hover:bg-[var(--rider-lime-2)] text-black text-[12px] font-semibold flex items-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {pending && <Loader2 className="w-3 h-3 animate-spin" />}
            {action.label}
          </button>
        ) : (
          <ChevronRight className="w-5 h-5 text-[var(--rider-muted)]" />
        )}
      </div>
    </article>
  );
}

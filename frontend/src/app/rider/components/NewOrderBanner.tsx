'use client';

// NewOrderBanner — accept/reject card at the top of the orders list.
// Currently UI-only: the parent passes `null` for newOrder because the
// dispatch-to-rider backend channel isn't wired up yet (followup PR).
// The card renders only when `order` is non-null.

import { Bell, MapPin } from 'lucide-react';

import type { RiderOrder } from '../lib/types';

interface NewOrderBannerProps {
  order: RiderOrder;
  onAccept: (order: RiderOrder) => void;
  onReject: (order: RiderOrder) => void;
}

export default function NewOrderBanner({
  order,
  onAccept,
  onReject,
}: NewOrderBannerProps) {
  return (
    <section className="mx-4 mt-3 rounded-2xl border border-[rgba(143,128,255,0.30)] bg-[rgba(143,128,255,0.08)] p-4 rider-slide-up">
      <div className="flex items-center gap-2 text-[var(--rider-violet)]">
        <Bell className="w-4 h-4" strokeWidth={2.5} />
        <h3 className="text-sm font-semibold">Pesanan Baru Untuk Anda</h3>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-[13px] text-white truncate">
            <span className="font-mono text-[var(--rider-text-2)]">
              #{order.order_number}
            </span>
            <span className="mx-1.5 text-[var(--rider-muted)]">·</span>
            <span className="font-medium">{order.customer_name}</span>
          </p>
          <p className="mt-0.5 text-[12px] text-[var(--rider-text-2)] truncate flex items-center gap-1">
            <MapPin className="w-3 h-3 shrink-0" />
            {order.delivery_address}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="font-mono text-[15px] font-semibold text-[var(--rider-lime)]">
            RM{order.total}
          </p>
          {order.distance_km && (
            <p className="text-[10px] text-[var(--rider-muted)]">
              {order.distance_km} km{order.eta_minutes ? ` · ~${order.eta_minutes} min` : ''}
            </p>
          )}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => onReject(order)}
          className="h-11 rounded-xl bg-[var(--rider-surface-2)] border border-[var(--rider-border)] text-[var(--rider-text-2)] text-sm font-medium hover:bg-[var(--rider-surface)] hover:text-white transition-colors"
        >
          Tolak
        </button>
        <button
          type="button"
          onClick={() => onAccept(order)}
          className="h-11 rounded-xl bg-[var(--rider-lime)] hover:bg-[var(--rider-lime-2)] text-black text-sm font-semibold transition-colors"
        >
          Terima
        </button>
      </div>
    </section>
  );
}

'use client';

import { Bike, Clock, MapPin } from 'lucide-react';
import type { ActiveOrder } from '../lib/types';
import StatusPill from './StatusPill';

function formatEta(etaAt: string | null): { text: string; tone: 'normal' | 'late' } {
  if (!etaAt) return { text: '—', tone: 'normal' };
  const diff = new Date(etaAt).getTime() - Date.now();
  const minutes = Math.round(diff / 60_000);
  if (minutes < 0) {
    return { text: `Lewat ${Math.abs(minutes)}m`, tone: 'late' };
  }
  if (minutes < 60) {
    return { text: `${minutes}m lagi`, tone: 'normal' };
  }
  return { text: `${Math.round(minutes / 60)}j lagi`, tone: 'normal' };
}

export default function OrderCard({
  order,
  selected,
  stuck = false,
  onClick,
  onHover,
  onHoverOut,
}: {
  order: ActiveOrder;
  selected: boolean;
  stuck?: boolean;
  onClick: () => void;
  onHover?: () => void;
  onHoverOut?: () => void;
}) {
  const eta = formatEta(order.eta_at);
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={onHover}
      onMouseLeave={onHoverOut}
      className={`w-full text-left rounded-xl px-3 py-3 transition border ${
        selected
          ? 'bg-white/[0.06] border-white/[0.16]'
          : 'bg-[#161623] border-white/[0.06] hover:border-white/[0.12]'
      } ${stuck ? 'ring-1 ring-red-400/40' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-mono text-[11px] tracking-wider text-white/50 uppercase truncate">
            {order.order_number}
          </div>
          <div className="mt-0.5 text-sm font-geist font-medium text-white truncate">
            {order.customer_name}
          </div>
        </div>
        <StatusPill status={order.status} />
      </div>

      <div className="mt-2 flex items-center gap-1.5 text-[11px] text-white/50">
        <MapPin size={12} strokeWidth={1.5} className="shrink-0" />
        <span className="truncate">{order.delivery_address}</span>
      </div>

      <div className="mt-2 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-1.5 text-white/60">
          <Bike size={12} strokeWidth={1.5} className="shrink-0" />
          <span className="truncate">
            {order.rider_name ?? <span className="text-white/40">Belum ada rider</span>}
          </span>
        </div>
        <div
          className={`flex items-center gap-1 font-mono ${
            eta.tone === 'late' ? 'text-red-300' : 'text-white/60'
          }`}
        >
          <Clock size={12} strokeWidth={1.5} className="shrink-0" />
          {eta.text}
        </div>
      </div>
    </button>
  );
}

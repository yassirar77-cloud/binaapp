'use client';

import { MapPin, Phone, User } from 'lucide-react';
import type { Order } from '../lib/types';
import MapThumbnail from './MapThumbnail';

interface Props {
  order: Order;
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .map((p) => p[0] ?? '')
    .join('')
    .slice(0, 2)
    .toUpperCase() || '?';
}

export default function CustomerInfoCard({ order }: Props) {
  return (
    <div className="rounded-xl bg-white/[0.03] ring-1 ring-white/[0.06] p-4">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-[#C7FF3D]/15 ring-1 ring-[#C7FF3D]/25 text-[#C7FF3D] flex items-center justify-center font-geist font-semibold text-xs">
          {initials(order.customer_name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-white/40 font-mono">
            <User size={11} strokeWidth={1.5} />
            Pelanggan
          </div>
          <div className="font-geist font-semibold text-sm text-white truncate">
            {order.customer_name}
          </div>
        </div>
      </div>

      <a
        href={`tel:${order.customer_phone}`}
        className="flex items-center gap-2 px-3 h-10 rounded-lg bg-white/[0.04] ring-1 ring-white/[0.06] hover:bg-white/[0.06] transition-colors font-mono text-xs text-[#C7FF3D] mb-3"
      >
        <Phone size={13} strokeWidth={1.5} className="text-white/50" />
        {order.customer_phone}
      </a>

      <div className="flex items-start gap-2 mb-3 text-xs font-geist text-white/75 leading-relaxed">
        <MapPin
          size={13}
          strokeWidth={1.5}
          className="text-white/40 shrink-0 mt-0.5"
        />
        <div className="min-w-0">
          {order.delivery_address}
          {order.delivery_notes ? (
            <div className="mt-1 text-[11px] text-white/50">
              <span className="text-white/40">Nota: </span>
              {order.delivery_notes}
            </div>
          ) : null}
        </div>
      </div>

      <MapThumbnail addressLine={order.delivery_address} />
    </div>
  );
}

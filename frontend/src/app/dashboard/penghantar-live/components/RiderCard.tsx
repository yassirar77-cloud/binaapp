'use client';

import { Bike, Hash, Package } from 'lucide-react';
import type { LiveRider } from '../lib/types';
import { computeRiderPresence } from '../lib/types';

const PRESENCE_LABEL: Record<
  ReturnType<typeof computeRiderPresence>,
  { label: string; dot: string; tone: string }
> = {
  online:           { label: 'Online',           dot: 'bg-emerald-400', tone: 'text-emerald-300' },
  online_stale_gps: { label: 'Online (GPS lapuk)', dot: 'bg-amber-400', tone: 'text-amber-300' },
  offline:          { label: 'Offline',          dot: 'bg-white/30',   tone: 'text-white/40' },
};

export default function RiderCard({
  rider,
  selected,
  onClick,
  onHover,
  onHoverOut,
}: {
  rider: LiveRider;
  selected: boolean;
  onClick: () => void;
  onHover?: () => void;
  onHoverOut?: () => void;
}) {
  const presence = computeRiderPresence(rider);
  const tone = PRESENCE_LABEL[presence];

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
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-geist font-medium text-white truncate">
            {rider.name}
          </div>
          {rider.vehicle_plate ? (
            <div className="mt-0.5 flex items-center gap-1 font-mono text-[11px] text-white/50">
              <Hash size={11} strokeWidth={1.5} className="shrink-0" />
              {rider.vehicle_plate}
            </div>
          ) : null}
        </div>
        <span
          className={`inline-flex items-center gap-1.5 h-5 px-2 rounded-full font-mono text-[10px] tracking-wide ${tone.tone} bg-white/[0.04] ring-1 ring-white/[0.06]`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
          {tone.label}
        </span>
      </div>

      <div className="mt-2 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-1.5 text-white/60">
          <Bike size={12} strokeWidth={1.5} className="shrink-0" />
          <span className="truncate">
            {rider.active_order_number ?? (
              <span className="text-white/40">Idle</span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-1 font-mono text-white/60">
          <Package size={12} strokeWidth={1.5} className="shrink-0" />
          {rider.today_deliveries}
        </div>
      </div>
    </button>
  );
}

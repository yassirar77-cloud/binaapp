'use client';

import { Bike, Phone } from 'lucide-react';
import type { Rider } from '../lib/types';

interface Props {
  rider: Rider;
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

export default function RiderInfoCard({ rider }: Props) {
  return (
    <div className="rounded-xl bg-indigo-400/[0.06] ring-1 ring-indigo-400/[0.18] p-4">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-indigo-400/15 ring-1 ring-indigo-400/30 text-indigo-300 flex items-center justify-center font-geist font-semibold text-xs">
          {initials(rider.name)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-indigo-300/80 font-mono">
            <Bike size={11} strokeWidth={1.5} />
            Rider
            <span
              className={`inline-flex items-center gap-1 h-4 px-1.5 rounded-full font-mono text-[9px] tracking-wider ${
                rider.is_online
                  ? 'bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/20'
                  : 'bg-white/[0.04] text-white/40 ring-1 ring-white/10'
              }`}
            >
              <span
                className={`h-1 w-1 rounded-full ${
                  rider.is_online ? 'bg-emerald-400' : 'bg-white/40'
                }`}
              />
              {rider.is_online ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="font-geist font-semibold text-sm text-white truncate">
            {rider.name}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <a
          href={`tel:${rider.phone}`}
          className="flex items-center gap-2 px-3 h-10 rounded-lg bg-white/[0.04] ring-1 ring-white/[0.06] hover:bg-white/[0.06] transition-colors font-mono text-xs text-[#C7FF3D]"
        >
          <Phone size={13} strokeWidth={1.5} className="text-white/50" />
          {rider.phone}
        </a>
        {rider.vehicle_plate ? (
          <div className="flex items-center gap-2 px-3 h-10 rounded-lg bg-white/[0.04] ring-1 ring-white/[0.06] font-mono text-xs text-white/80">
            <span className="text-[10px] uppercase text-white/40 tracking-wider">
              Plat
            </span>
            <span className="truncate">{rider.vehicle_plate}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

'use client';

import { ChevronDown, Store } from 'lucide-react';
import type { Outlet, Zone } from '../lib/types';
import { formatKm2, polygonAreaM2 } from '../lib/polygon';

export default function TopBar({
  outlets,
  selectedOutletId,
  onOutletChange,
  zones,
}: {
  outlets: Outlet[];
  selectedOutletId: string | null;
  onOutletChange: (id: string) => void;
  zones: Zone[];
}) {
  const activeCount = zones.filter((z) => z.active).length;
  const avgFeeCents =
    zones.length > 0
      ? zones.reduce((sum, z) => sum + z.fee_cents, 0) / zones.length
      : 0;
  const totalAreaM2 = zones.reduce(
    (sum, z) => sum + (z.area_m2 ?? polygonAreaM2(z.polygon)),
    0,
  );

  const stats: Array<{ label: string; value: string }> = [
    { label: 'Zon Aktif', value: String(activeCount) },
    { label: 'Yuran Purata', value: `RM ${(avgFeeCents / 100).toFixed(2)}` },
    { label: 'Liputan', value: `${formatKm2(totalAreaM2)} km²` },
  ];

  return (
    <div className="w-full px-4 lg:px-6 py-4 border-b border-white/[0.08] bg-[#0a0e1a]/95 backdrop-blur-sm sticky top-0 z-20">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="font-geist font-semibold text-lg sm:text-xl text-white tracking-[-0.02em] shrink-0">
            Urus Penghantaran
          </h1>
          {outlets.length > 0 && (
            <div className="relative shrink min-w-0">
              <Store
                size={14}
                strokeWidth={1.5}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
              <select
                value={selectedOutletId ?? ''}
                onChange={(e) => onOutletChange(e.target.value)}
                className="appearance-none h-10 pl-9 pr-9 max-w-[240px] truncate rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist focus:outline-none focus:border-white/[0.16]"
              >
                {outlets.map((o) => (
                  <option key={o.id} value={o.id} className="bg-[#161623]">
                    {o.name}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={14}
                strokeWidth={1.5}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
            </div>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3 sm:gap-6">
          {stats.map((s) => (
            <div key={s.label} className="text-right">
              <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
                {s.label}
              </div>
              <div className="font-mono font-semibold text-base sm:text-lg text-white">
                {s.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

'use client';

import { ChevronDown, Store } from 'lucide-react';
import type { ActiveOrder, LiveRider, Outlet } from '../lib/types';
import { computeRiderPresence } from '../lib/types';

const IN_PROGRESS_STATUSES = new Set(['picked_up', 'delivering']);

export default function TopBar({
  outlets,
  selectedOutletId,
  onOutletChange,
  orders,
  riders,
  stuckCount,
}: {
  outlets: Outlet[];
  selectedOutletId: string | null;
  onOutletChange: (id: string) => void;
  orders: ActiveOrder[];
  riders: LiveRider[];
  stuckCount: number;
}) {
  const inProgress = orders.filter((o) => IN_PROGRESS_STATUSES.has(o.status)).length;
  const onlineRiders = riders.filter(
    (r) => computeRiderPresence(r) !== 'offline',
  ).length;

  const stats: Array<{ label: string; value: string; tone: 'normal' | 'alert' }> = [
    { label: 'Dalam Perjalanan', value: String(inProgress), tone: 'normal' },
    { label: 'Rider Online', value: `${onlineRiders}/${riders.length}`, tone: 'normal' },
    { label: 'Tersangkut', value: String(stuckCount), tone: stuckCount > 0 ? 'alert' : 'normal' },
  ];

  return (
    <div className="w-full px-4 lg:px-6 py-4 border-b border-white/[0.08] bg-[#0a0e1a]/95 backdrop-blur-sm sticky top-0 z-20">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="font-geist font-semibold text-lg sm:text-xl text-white tracking-[-0.02em] shrink-0">
            Penghantar Live
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
              <div
                className={`font-mono font-semibold text-base sm:text-lg ${
                  s.tone === 'alert' ? 'text-red-300' : 'text-white'
                }`}
              >
                {s.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

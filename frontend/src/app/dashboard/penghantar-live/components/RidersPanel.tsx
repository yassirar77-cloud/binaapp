'use client';

import { useMemo, useState } from 'react';
import { Users } from 'lucide-react';
import type { LiveRider } from '../lib/types';
import { computeRiderPresence } from '../lib/types';
import RiderCard from './RiderCard';

type FilterKey = 'all' | 'online' | 'idle';

const FILTERS: Array<{ key: FilterKey; label: string }> = [
  { key: 'all', label: 'Semua' },
  { key: 'online', label: 'Online' },
  { key: 'idle', label: 'Idle' },
];

function applyFilter(riders: LiveRider[], key: FilterKey): LiveRider[] {
  if (key === 'all') return riders;
  if (key === 'online') {
    return riders.filter((r) => computeRiderPresence(r) !== 'offline');
  }
  // Idle = online + no active order
  return riders.filter(
    (r) =>
      computeRiderPresence(r) !== 'offline' && !r.active_order_id,
  );
}

export default function RidersPanel({
  riders,
  selectedId,
  showOffline,
  onSelect,
  onHover,
}: {
  riders: LiveRider[];
  selectedId: string | null;
  showOffline: boolean;
  onSelect: (riderId: string) => void;
  onHover?: (riderId: string | null) => void;
}) {
  const [filter, setFilter] = useState<FilterKey>('all');
  const filtered = useMemo(() => {
    const base = showOffline
      ? riders
      : riders.filter((r) => computeRiderPresence(r) !== 'offline');
    return applyFilter(base, filter);
  }, [riders, filter, showOffline]);

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#0a0e1a] border-t border-white/[0.06]">
      <div className="px-3 pt-3 pb-2 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-geist text-sm font-semibold text-white">Rider</h2>
          <span className="font-mono text-[11px] text-white/40">
            {riders.length}
          </span>
        </div>
        <div className="flex gap-1.5">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              onClick={() => setFilter(f.key)}
              className={`h-7 px-2.5 rounded-full text-[11px] font-mono tracking-wide transition ${
                filter === f.key
                  ? 'bg-white text-[#0a0e1a]'
                  : 'bg-white/[0.04] text-white/60 hover:bg-white/[0.08]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-2">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-white/40">
            <Users size={20} strokeWidth={1.5} />
            <p className="mt-2 text-xs font-geist">Tiada rider</p>
          </div>
        ) : (
          filtered.map((r) => (
            <RiderCard
              key={r.id}
              rider={r}
              selected={selectedId === r.id}
              onClick={() => onSelect(r.id)}
              onHover={() => onHover?.(r.id)}
              onHoverOut={() => onHover?.(null)}
            />
          ))
        )}
      </div>
    </div>
  );
}

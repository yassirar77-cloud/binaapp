'use client';

import { useMemo, useState } from 'react';
import { Inbox } from 'lucide-react';
import type { ActiveOrder, OrderStatus } from '../lib/types';
import OrderCard from './OrderCard';

type FilterKey = 'all' | 'unassigned' | 'in_progress';

const FILTERS: Array<{ key: FilterKey; label: string }> = [
  { key: 'all', label: 'Semua' },
  { key: 'unassigned', label: 'Belum rider' },
  { key: 'in_progress', label: 'Dalam perjalanan' },
];

const IN_PROGRESS_STATUSES: ReadonlySet<OrderStatus> = new Set([
  'picked_up',
  'delivering',
]);

function applyFilter(orders: ActiveOrder[], key: FilterKey): ActiveOrder[] {
  if (key === 'all') return orders;
  if (key === 'unassigned') return orders.filter((o) => !o.rider_id);
  return orders.filter((o) => IN_PROGRESS_STATUSES.has(o.status));
}

export default function OrdersPanel({
  orders,
  selectedId,
  stuckOrderIds,
  onSelect,
  onHover,
}: {
  orders: ActiveOrder[];
  selectedId: string | null;
  stuckOrderIds: ReadonlySet<string>;
  onSelect: (orderId: string) => void;
  onHover?: (orderId: string | null) => void;
}) {
  const [filter, setFilter] = useState<FilterKey>('all');
  const filtered = useMemo(() => applyFilter(orders, filter), [orders, filter]);

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#0a0e1a]">
      <div className="px-3 pt-3 pb-2 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-geist text-sm font-semibold text-white">
            Pesanan Aktif
          </h2>
          <span className="font-mono text-[11px] text-white/40">
            {orders.length}
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
            <Inbox size={20} strokeWidth={1.5} />
            <p className="mt-2 text-xs font-geist">Tiada pesanan</p>
          </div>
        ) : (
          filtered.map((o) => (
            <OrderCard
              key={o.id}
              order={o}
              selected={selectedId === o.id}
              stuck={stuckOrderIds.has(o.id)}
              onClick={() => onSelect(o.id)}
              onHover={() => onHover?.(o.id)}
              onHoverOut={() => onHover?.(null)}
            />
          ))
        )}
      </div>
    </div>
  );
}

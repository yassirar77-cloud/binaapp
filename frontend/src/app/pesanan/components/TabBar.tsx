'use client';

import type { Order, TabKey } from '../lib/types';
import { TABS, statusMeta } from '../lib/constants';

interface Props {
  tab: TabKey;
  onTabChange: (next: TabKey) => void;
  orders: Order[];
  lastRefresh: Date | null;
}

/** Count orders that belong to a tab via STATUS_META.tab. */
function countForTab(orders: Order[], key: TabKey): number {
  if (key === 'semua') return orders.length;
  let n = 0;
  for (const o of orders) {
    if (statusMeta(o.status).tab === key) n++;
  }
  return n;
}

function formatTime(d: Date | null): string {
  if (!d) return '—';
  return d.toLocaleTimeString('ms-MY', { hour: '2-digit', minute: '2-digit' });
}

export default function TabBar({ tab, onTabChange, orders, lastRefresh }: Props) {
  return (
    <div className="w-full px-4 lg:px-6 border-b border-white/[0.06] bg-[#0a0e1a]">
      <div className="flex items-center justify-between gap-4">
        <div
          className="pesanan-tabs-scroll flex items-center gap-1 overflow-x-auto -mb-px"
          role="tablist"
        >
          {TABS.map(({ key, label }) => {
            const active = tab === key;
            const count = countForTab(orders, key);
            return (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => onTabChange(key)}
                className={[
                  'shrink-0 inline-flex items-center gap-2 px-3 sm:px-4 h-11',
                  'border-b-2 font-geist text-sm transition-colors',
                  active
                    ? 'border-[#C7FF3D] text-white'
                    : 'border-transparent text-white/55 hover:text-white/80',
                ].join(' ')}
              >
                <span>{label}</span>
                {count > 0 && (
                  <span
                    className={[
                      'inline-flex items-center justify-center min-w-[18px] h-[18px] px-1.5',
                      'rounded-full font-mono text-[10px] tracking-wide',
                      active
                        ? 'bg-[#C7FF3D]/15 text-[#C7FF3D] ring-1 ring-[#C7FF3D]/30'
                        : 'bg-white/[0.06] text-white/60 ring-1 ring-white/10',
                    ].join(' ')}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="hidden sm:flex items-center gap-2 shrink-0">
          <span className="inline-flex items-center gap-1.5 h-6 px-2 rounded-full bg-emerald-400/10 ring-1 ring-emerald-400/20">
            <span className="pesanan-live-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="font-mono text-[10px] tracking-wider uppercase text-emerald-300">
              Live
            </span>
          </span>
          <span className="font-mono text-[10px] tracking-wide text-white/40">
            {formatTime(lastRefresh)}
          </span>
        </div>
      </div>
    </div>
  );
}

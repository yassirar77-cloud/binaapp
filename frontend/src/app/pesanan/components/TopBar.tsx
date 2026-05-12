'use client';

import { Bell, ChevronDown, RefreshCw, Store } from 'lucide-react';
import type { Order, Website } from '../lib/types';

interface Props {
  websites: Website[];
  selectedWebsiteId: string | 'all';
  onWebsiteChange: (id: string | 'all') => void;
  orders: Order[];
  pendingCount: number;
  loading: boolean;
  onRefresh: () => void;
}

function isToday(iso: string, now: Date = new Date()): boolean {
  const d = new Date(iso);
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

function formatRM(n: number): string {
  return `RM ${n.toFixed(2)}`;
}

export default function TopBar({
  websites,
  selectedWebsiteId,
  onWebsiteChange,
  orders,
  pendingCount,
  loading,
  onRefresh,
}: Props) {
  const todays = orders.filter((o) => isToday(o.created_at));
  const todayCount = todays.length;
  const todaySales = todays
    .filter((o) => o.status !== 'cancelled' && o.status !== 'rejected')
    .reduce((sum, o) => sum + (o.total_amount ?? 0), 0);

  const stats: Array<{ label: string; value: string; tone: 'normal' | 'alert' }> = [
    { label: 'Hari Ini',  value: String(todayCount), tone: 'normal' },
    { label: 'Menunggu',  value: String(pendingCount), tone: pendingCount > 0 ? 'alert' : 'normal' },
    { label: 'Jualan',    value: formatRM(todaySales), tone: 'normal' },
  ];

  return (
    <div className="w-full px-4 lg:px-6 py-4 border-b border-white/[0.08] bg-[#0a0e1a]/95 backdrop-blur-sm sticky top-0 z-20">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="font-geist font-semibold text-lg sm:text-xl text-white tracking-[-0.02em] shrink-0">
            Pesanan
          </h1>
          {websites.length > 0 && (
            <div className="relative shrink min-w-0">
              <Store
                size={14}
                strokeWidth={1.5}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
              <select
                value={selectedWebsiteId}
                onChange={(e) => onWebsiteChange(e.target.value)}
                className="appearance-none h-10 pl-9 pr-9 max-w-[240px] truncate rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist focus:outline-none focus:border-white/[0.16]"
              >
                <option value="all" className="bg-[#161623]">
                  Semua outlet
                </option>
                {websites.map((w) => (
                  <option key={w.id} value={w.id} className="bg-[#161623]">
                    {w.name || w.business_name || 'Outlet'}
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

        <div className="flex items-center gap-3">
          {/* Compact mobile stat: single line, hides on md+. */}
          <div className="md:hidden flex items-center gap-2">
            <span className="font-mono text-[11px] tracking-wide text-white/50">
              {todayCount} hari ini
            </span>
            {pendingCount > 0 && (
              <span className="inline-flex items-center gap-1 h-5 px-2 rounded-full font-mono text-[10px] tracking-wide text-amber-300 bg-amber-400/10 ring-1 ring-amber-400/20">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                {pendingCount}
              </span>
            )}
          </div>

          <div className="hidden md:grid grid-cols-3 gap-6">
            {stats.map((s) => (
              <div key={s.label} className="text-right">
                <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
                  {s.label}
                </div>
                <div
                  className={`font-mono font-semibold text-base sm:text-lg ${
                    s.tone === 'alert' ? 'text-amber-300' : 'text-white'
                  }`}
                >
                  {s.value}
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-1.5 ml-2">
            <button
              type="button"
              aria-label="Notifikasi"
              className="relative inline-flex items-center justify-center w-10 h-10 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors"
            >
              <Bell size={16} strokeWidth={1.5} />
              {pendingCount > 0 && (
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-amber-400 ring-2 ring-[#0a0e1a]" />
              )}
            </button>
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              aria-label="Refresh"
              className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors disabled:opacity-50"
            >
              <RefreshCw
                size={16}
                strokeWidth={1.5}
                className={loading ? 'animate-spin' : ''}
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

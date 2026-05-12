'use client';

import { CalendarDays, ChevronDown, RefreshCw, Search, Store } from 'lucide-react';
import type { DateRange, Website } from '../lib/types';
import { DATE_RANGE_LABELS } from '../lib/constants';

interface Props {
  searchQuery: string;
  onSearchChange: (next: string) => void;
  dateRange: DateRange;
  onDateRangeChange: (next: DateRange) => void;
  websites: Website[];
  selectedWebsiteId: string | 'all';
  onWebsiteChange: (id: string | 'all') => void;
  loading: boolean;
  onRefresh: () => void;
}

export default function FilterBar({
  searchQuery,
  onSearchChange,
  dateRange,
  onDateRangeChange,
  websites,
  selectedWebsiteId,
  onWebsiteChange,
  loading,
  onRefresh,
}: Props) {
  return (
    <div className="w-full px-4 lg:px-6 py-3 border-b border-white/[0.06] bg-[#0a0e1a]">
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-0 sm:max-w-md">
          <Search
            size={14}
            strokeWidth={1.5}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none"
          />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Cari no. pesanan, nama, telefon…"
            className="w-full h-10 pl-9 pr-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white placeholder:text-white/30 font-geist focus:outline-none focus:border-white/[0.16]"
          />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Date range */}
          <div className="relative">
            <CalendarDays
              size={14}
              strokeWidth={1.5}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
            />
            <select
              value={dateRange}
              onChange={(e) => onDateRangeChange(e.target.value as DateRange)}
              className="appearance-none h-10 pl-9 pr-9 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist focus:outline-none focus:border-white/[0.16]"
            >
              {(['today','yesterday','7days','30days'] as DateRange[]).map((k) => (
                <option key={k} value={k} className="bg-[#161623]">
                  {DATE_RANGE_LABELS[k]}
                </option>
              ))}
            </select>
            <ChevronDown
              size={14}
              strokeWidth={1.5}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
            />
          </div>

          {/* Outlet filter (shown only when owner has 2+ outlets — for single
              outlet it duplicates the TopBar selector). */}
          {websites.length > 1 && (
            <div className="relative hidden md:block">
              <Store
                size={14}
                strokeWidth={1.5}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
              <select
                value={selectedWebsiteId}
                onChange={(e) => onWebsiteChange(e.target.value)}
                className="appearance-none h-10 pl-9 pr-9 max-w-[180px] truncate rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist focus:outline-none focus:border-white/[0.16]"
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

          {/* Refresh (secondary; TopBar carries the primary one) */}
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            aria-label="Refresh"
            className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors disabled:opacity-50"
          >
            <RefreshCw
              size={14}
              strokeWidth={1.5}
              className={loading ? 'animate-spin' : ''}
            />
          </button>
        </div>
      </div>
    </div>
  );
}

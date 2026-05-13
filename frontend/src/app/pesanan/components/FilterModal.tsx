'use client';

// Filter modal used on mobile where the FilterBar collapses to search + a
// "Filter" trigger. Holds buffered (pending) state internally and only
// commits to the parent on Apply. Reset is "apply defaults + close" — i.e.
// show everything from today.
//
// Layout swaps between bottom sheet (mobile, slide-up) and centered modal
// (desktop fallback, scale-in) at the md breakpoint so the same component
// can be used in both contexts if we ever surface it on desktop too.

import { useEffect, useState } from 'react';
import { CalendarDays, ChevronDown, RotateCcw, Store, X } from 'lucide-react';
import type { DateRange, Website } from '../lib/types';
import { DATE_RANGE_LABELS } from '../lib/constants';

interface Props {
  websites: Website[];
  dateRange: DateRange;
  selectedWebsiteId: string | 'all';
  onClose: () => void;
  onApply: (next: { dateRange: DateRange; selectedWebsiteId: string | 'all' }) => void;
}

const DEFAULT_DATE_RANGE: DateRange = 'today';
const DEFAULT_WEBSITE: 'all' = 'all';

export default function FilterModal({
  websites,
  dateRange,
  selectedWebsiteId,
  onClose,
  onApply,
}: Props) {
  const [pendingRange, setPendingRange] = useState<DateRange>(dateRange);
  const [pendingWebsite, setPendingWebsite] = useState<string | 'all'>(
    selectedWebsiteId,
  );

  // ESC closes.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const apply = () =>
    onApply({ dateRange: pendingRange, selectedWebsiteId: pendingWebsite });

  const reset = () => {
    setPendingRange(DEFAULT_DATE_RANGE);
    setPendingWebsite(DEFAULT_WEBSITE);
    onApply({
      dateRange: DEFAULT_DATE_RANGE,
      selectedWebsiteId: DEFAULT_WEBSITE,
    });
  };

  return (
    <div
      className="pesanan-fade-in fixed inset-0 z-[60] bg-black/55 backdrop-blur-sm flex items-end md:items-center justify-center md:p-4"
      onMouseDown={onClose}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Penapis"
        onMouseDown={(e) => e.stopPropagation()}
        className="pesanan-slide-up md:pesanan-modal-in w-full md:max-w-[420px] md:w-[420px] bg-[#161623] ring-1 ring-white/[0.08] shadow-2xl shadow-black/50 rounded-t-2xl md:rounded-xl overflow-hidden flex flex-col max-h-[85vh] md:max-h-[80vh]"
      >
        {/* Grabber + header */}
        <div className="shrink-0 px-5 pt-3 pb-3 border-b border-white/[0.06]">
          <div className="md:hidden mx-auto mb-3 h-1 w-10 rounded-full bg-white/15" />
          <div className="flex items-center justify-between">
            <h2 className="font-geist font-semibold text-sm text-white">
              Penapis
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Tutup"
              className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-white/60 hover:text-white ring-1 ring-white/[0.06] transition-colors"
            >
              <X size={14} strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {/* Date range */}
          <div>
            <label className="block font-mono text-[10px] uppercase tracking-wider text-white/45 mb-1.5">
              Tarikh
            </label>
            <div className="relative">
              <CalendarDays
                size={14}
                strokeWidth={1.5}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
              <select
                value={pendingRange}
                onChange={(e) => setPendingRange(e.target.value as DateRange)}
                className="appearance-none w-full h-11 pl-9 pr-9 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist focus:outline-none focus:border-white/[0.16]"
              >
                {(['today', 'yesterday', '7days', '30days'] as DateRange[]).map(
                  (k) => (
                    <option key={k} value={k} className="bg-[#161623]">
                      {DATE_RANGE_LABELS[k]}
                    </option>
                  ),
                )}
              </select>
              <ChevronDown
                size={14}
                strokeWidth={1.5}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
            </div>
          </div>

          {/* Outlet — only shown for multi-outlet accounts. */}
          {websites.length > 1 ? (
            <div>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-white/45 mb-1.5">
                Outlet
              </label>
              <div className="relative">
                <Store
                  size={14}
                  strokeWidth={1.5}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
                />
                <select
                  value={pendingWebsite}
                  onChange={(e) => setPendingWebsite(e.target.value)}
                  className="appearance-none w-full h-11 pl-9 pr-9 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist focus:outline-none focus:border-white/[0.16]"
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
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
                />
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="shrink-0 grid grid-cols-[auto_1fr] gap-2 px-5 pt-3 pb-5 border-t border-white/[0.06]">
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center justify-center gap-1.5 h-11 px-4 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] ring-1 ring-white/[0.08] text-white/80 font-geist text-sm font-medium transition-colors"
          >
            <RotateCcw size={14} strokeWidth={1.5} />
            Reset
          </button>
          <button
            type="button"
            onClick={apply}
            className="inline-flex items-center justify-center h-11 px-4 rounded-lg bg-[#C7FF3D] hover:bg-[#d8ff6b] active:bg-[#b5e633] text-[#0B0B15] font-geist text-sm font-semibold transition-colors"
          >
            Gunakan Penapis
          </button>
        </div>
      </div>
    </div>
  );
}

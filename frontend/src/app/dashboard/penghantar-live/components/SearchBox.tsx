'use client';

// SearchBox — filters both list panels (orders + riders) by one query.
// The map intentionally keeps showing everything.

import { Search, X } from 'lucide-react';

export default function SearchBox({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="px-3 pt-3 pb-1">
      <div className="relative">
        <Search
          size={14}
          strokeWidth={1.5}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none"
        />
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Cari pesanan atau rider…"
          aria-label="Cari pesanan atau rider"
          className="w-full h-9 pl-9 pr-8 rounded-lg bg-white/[0.04] border border-white/[0.08] text-[13px] text-white font-geist placeholder:text-white/30 focus:outline-none focus:border-white/[0.16] [&::-webkit-search-cancel-button]:hidden"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            aria-label="Kosongkan carian"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 h-6 w-6 flex items-center justify-center rounded text-white/40 hover:text-white hover:bg-white/[0.06] transition"
          >
            <X size={12} strokeWidth={1.5} />
          </button>
        )}
      </div>
    </div>
  );
}

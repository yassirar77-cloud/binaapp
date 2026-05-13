'use client';

// Search input for the conversation list. Controlled — debouncing happens in
// the parent (ChatClient) so this stays a pure presentational input.

import { Search, X } from 'lucide-react';

interface Props {
  value: string;
  onChange: (next: string) => void;
}

export default function SearchBar({ value, onChange }: Props) {
  return (
    <div className="px-3 py-2 border-b border-white/[0.06]">
      <div className="relative">
        <Search
          size={14}
          strokeWidth={1.5}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Cari nama, telefon, pesanan…"
          className="w-full h-9 pl-9 pr-9 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs sm:text-sm text-white placeholder:text-white/30 font-geist focus:outline-none focus:border-white/[0.16]"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange('')}
            aria-label="Padam carian"
            className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center justify-center w-6 h-6 rounded text-white/40 hover:text-white/80 hover:bg-white/[0.06] transition-colors"
          >
            <X size={12} strokeWidth={2} />
          </button>
        )}
      </div>
    </div>
  );
}

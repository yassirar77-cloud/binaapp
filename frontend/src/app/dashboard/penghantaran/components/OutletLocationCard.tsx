'use client';

import { MapPin, Move } from 'lucide-react';

export default function OutletLocationCard({
  address,
  hasLocation,
  picking,
  onTogglePick,
}: {
  address: string | null;
  hasLocation: boolean;
  picking: boolean;
  onTogglePick: () => void;
}) {
  if (!hasLocation) {
    return (
      <div className="rounded-xl bg-[#161623] border border-[#C7FF3D]/30 p-4">
        <div className="flex items-center gap-2 mb-1.5">
          <MapPin size={14} strokeWidth={1.5} className="text-[#C7FF3D]" />
          <span className="font-mono text-[10px] tracking-wider uppercase text-[#C7FF3D]">
            Tetapkan lokasi kedai dahulu
          </span>
        </div>
        <p className="text-xs text-white/60 mb-3">
          Klik pada peta untuk menanda lokasi kedai. Ring penghantaran akan
          dikira dari titik ini.
        </p>
        <button
          type="button"
          onClick={onTogglePick}
          className={`w-full inline-flex items-center justify-center gap-1.5 h-9 px-3 rounded-lg font-geist font-semibold text-sm transition ${
            picking
              ? 'bg-white/[0.08] text-white border border-white/[0.16]'
              : 'bg-[#C7FF3D] text-black hover:brightness-110'
          }`}
        >
          {picking ? 'Batal' : 'Tetapkan Lokasi'}
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-[#161623] border border-white/[0.08] p-4">
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <MapPin size={14} strokeWidth={1.5} className="text-[#C7FF3D] shrink-0" />
          <span className="font-mono text-[10px] tracking-wider uppercase text-white/60">
            Lokasi Kedai
          </span>
        </div>
      </div>
      <div className="text-sm text-white/80 mb-3 line-clamp-2">
        {address || 'Pin diset di peta'}
      </div>
      <button
        type="button"
        onClick={onTogglePick}
        className={`inline-flex items-center gap-1.5 h-8 px-3 rounded-lg font-geist font-medium text-xs transition ${
          picking
            ? 'bg-[#C7FF3D] text-black hover:brightness-110'
            : 'bg-white/[0.06] text-white hover:bg-white/[0.1]'
        }`}
      >
        <Move size={12} strokeWidth={2} />
        {picking ? 'Klik peta…' : 'Tukar lokasi'}
      </button>
    </div>
  );
}

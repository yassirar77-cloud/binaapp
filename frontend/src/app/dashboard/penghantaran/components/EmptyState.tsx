'use client';

import { Plus } from 'lucide-react';

export default function EmptyState({
  onAddZone,
  disabled,
}: {
  onAddZone: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center px-6 py-12 rounded-xl bg-white/[0.02] border border-white/[0.06]">
      <svg
        width="44"
        height="44"
        viewBox="0 0 24 24"
        fill="none"
        stroke="rgba(255,255,255,0.4)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 21s-7-7.5-7-12a7 7 0 1 1 14 0c0 4.5-7 12-7 12z" />
        <circle cx="12" cy="9" r="2.5" />
      </svg>
      <h3 className="mt-4 font-geist font-semibold text-base text-white">
        Belum ada zon penghantaran
      </h3>
      <p className="mt-1 text-sm text-white/60 max-w-xs">
        Lukis zon pertama anda di peta untuk mula menerima pesanan delivery.
      </p>
      <button
        type="button"
        onClick={onAddZone}
        disabled={disabled}
        className="mt-5 inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-[#C7FF3D] text-black font-geist font-semibold text-sm hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        <Plus size={16} strokeWidth={2} />
        Lukis Zon Pertama
      </button>
    </div>
  );
}

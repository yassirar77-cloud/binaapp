'use client';

// StuckBanner — top-center alert when at least 1 order is stuck.
// Clicking the banner selects the first stuck order so the owner can act.

import { AlertTriangle } from 'lucide-react';

interface Props {
  count: number;
  firstStuckOrderId: string | null;
  onSelectStuck: (orderId: string) => void;
}

export default function StuckBanner({ count, firstStuckOrderId, onSelectStuck }: Props) {
  if (count === 0) return null;
  return (
    <button
      type="button"
      onClick={() => {
        if (firstStuckOrderId) onSelectStuck(firstStuckOrderId);
      }}
      className="phl-stuck-banner absolute top-3 left-1/2 -translate-x-1/2 z-[1000] inline-flex items-center gap-2 px-3.5 h-10 rounded-full bg-red-400/15 border border-red-400/40 text-red-300 hover:bg-red-400/20 transition"
    >
      <AlertTriangle size={14} strokeWidth={1.5} />
      <span className="font-geist text-[13px] font-medium">
        {count === 1
          ? '1 pesanan tersangkut'
          : `${count} pesanan tersangkut`}
      </span>
      <span className="font-mono text-[11px] text-red-300/70 hidden sm:inline">
        Klik untuk lihat
      </span>
    </button>
  );
}

'use client';

import { Inbox, SearchX } from 'lucide-react';

/** Two empty-state variants: no orders at all vs. filter mismatch. The
 *  copy is fixed in Malay; pass `variant` to swap the illustration + text. */

interface Props {
  variant: 'no-orders' | 'no-match';
}

export default function EmptyState({ variant }: Props) {
  const isNoMatch = variant === 'no-match';
  const Icon = isNoMatch ? SearchX : Inbox;
  const heading = isNoMatch
    ? 'Tiada pesanan menepati pencarian anda'
    : 'Tiada pesanan lagi';
  const sub = isNoMatch
    ? 'Cuba ubah penapis atau tarikh.'
    : 'Pesanan baru akan muncul di sini sebaik sahaja diterima.';

  return (
    <div className="flex flex-col items-center justify-center text-center py-20 px-4">
      <div className="mb-4 inline-flex items-center justify-center w-14 h-14 rounded-full bg-white/[0.04] ring-1 ring-white/[0.08] text-white/50">
        <Icon size={22} strokeWidth={1.5} />
      </div>
      <p className="text-sm text-white/70 font-geist">{heading}</p>
      <p className="mt-1 text-xs text-white/40 font-geist">{sub}</p>
    </div>
  );
}

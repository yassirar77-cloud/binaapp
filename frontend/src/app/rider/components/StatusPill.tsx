'use client';

// StatusPill — colored badge driven by STATUS_META. The single source of
// truth for status labels + colors in the rider PWA.

import { STATUS_META } from '../lib/constants';
import type { OrderStatus } from '../lib/types';

interface StatusPillProps {
  status: OrderStatus;
  size?: 'sm' | 'md';
}

export default function StatusPill({ status, size = 'md' }: StatusPillProps) {
  const meta = STATUS_META[status];
  if (!meta) return null;

  const padding = size === 'sm' ? 'px-2 py-0.5' : 'px-2.5 py-1';
  const text = size === 'sm' ? 'text-[10px]' : 'text-[11px]';

  return (
    <span
      className={`inline-flex items-center gap-1.5 ${padding} ${text} font-medium rounded-full border whitespace-nowrap`}
      style={{
        color: meta.color,
        backgroundColor: meta.bg,
        borderColor: meta.border,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: meta.color }}
      />
      {meta.label}
    </span>
  );
}

'use client';

// Status pill: solid dot + Malay label. Two sizes (sm for cards, md for the
// detail panel header). Unknown statuses fall through STATUS_META_FALLBACK
// (gray) via statusMeta() — never crashes on a legacy enum value.

import type { Order } from '../lib/types';
import { statusMeta } from '../lib/constants';

interface Props {
  status: Order['status'];
  size?: 'sm' | 'md';
}

export default function StatusPill({ status, size = 'sm' }: Props) {
  const meta = statusMeta(status);
  const dims =
    size === 'md' ? 'h-7 px-2.5 text-[11px]' : 'h-5 px-2 text-[10px]';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-mono tracking-wide ${dims}`}
      style={{
        backgroundColor: `${meta.color}1a`,
        color: meta.color,
        boxShadow: `inset 0 0 0 1px ${meta.color}33`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: meta.color }}
      />
      {meta.label}
    </span>
  );
}

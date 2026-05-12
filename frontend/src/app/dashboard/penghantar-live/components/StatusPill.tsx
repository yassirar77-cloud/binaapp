'use client';

import type { OrderStatus } from '../lib/types';
import { STATUS_LABELS_MS } from '../lib/types';

interface StyleSpec {
  /** Tailwind text + bg classes for the pill body. */
  classes: string;
  /** Solid dot color used inside the pill. */
  dot: string;
}

const STYLES: Record<OrderStatus, StyleSpec> = {
  pending:    { classes: 'bg-amber-400/10  text-amber-300  ring-1 ring-amber-400/20',  dot: 'bg-amber-400'  },
  confirmed:  { classes: 'bg-cyan-400/10   text-cyan-300   ring-1 ring-cyan-400/20',   dot: 'bg-cyan-400'   },
  preparing:  { classes: 'bg-violet-400/10 text-violet-300 ring-1 ring-violet-400/20', dot: 'bg-violet-400' },
  ready:      { classes: 'bg-blue-400/10   text-blue-300   ring-1 ring-blue-400/20',   dot: 'bg-blue-400'   },
  picked_up:  { classes: 'bg-[#C7FF3D]/10  text-[#C7FF3D]  ring-1 ring-[#C7FF3D]/30',  dot: 'bg-[#C7FF3D]'  },
  delivering: { classes: 'bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/20', dot: 'bg-emerald-400' },
  delivered:  { classes: 'bg-white/5       text-white/50   ring-1 ring-white/10',      dot: 'bg-white/40'   },
  completed:  { classes: 'bg-white/5       text-white/50   ring-1 ring-white/10',      dot: 'bg-white/40'   },
  cancelled:  { classes: 'bg-red-400/10    text-red-300    ring-1 ring-red-400/20',    dot: 'bg-red-400'    },
};

export default function StatusPill({
  status,
  size = 'sm',
}: {
  status: OrderStatus;
  size?: 'sm' | 'md';
}) {
  const style = STYLES[status];
  const label = STATUS_LABELS_MS[status];
  const sizeClasses =
    size === 'md'
      ? 'h-7 px-2.5 text-[11px]'
      : 'h-5 px-2 text-[10px]';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-mono tracking-wide ${sizeClasses} ${style.classes}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {label}
    </span>
  );
}

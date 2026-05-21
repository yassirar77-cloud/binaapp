'use client';

import type { ReactNode } from 'react';

export default function SectionHeader({
  eyebrow,
  title,
  sub,
  right,
}: {
  eyebrow: string;
  title: string;
  sub?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <div className="font-geist-mono text-[10.5px] font-semibold uppercase tracking-[0.14em] text-brand-500">
          — {eyebrow}
        </div>
        <h3 className="mt-1.5 text-[22px] font-bold tracking-[-0.03em] text-ink-900">{title}</h3>
        {sub && <p className="mt-1 text-[13px] text-ink-400">{sub}</p>}
      </div>
      {right && <div className="flex-shrink-0">{right}</div>}
    </div>
  );
}

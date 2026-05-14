'use client';

// Empty-state variants used by the list and the right panel.
// - 'no-convs'     : owner has zero conversations at all (or none on this outlet).
// - 'no-match'     : current filter combo has no results.
// - 'no-selection' : list has rows but nothing selected on the right panel.

import { MessageSquare, SearchX, MousePointerClick } from 'lucide-react';

type Variant = 'no-convs' | 'no-match' | 'no-selection';

export interface EmptyStateStat {
  label: string;
  value: string | number;
  tone?: 'normal' | 'accent' | 'alert';
}

interface Props {
  variant: Variant;
  stats?: EmptyStateStat[];
  className?: string;
}

const COPY: Record<Variant, { icon: typeof MessageSquare; title: string; body: string }> = {
  'no-convs': {
    icon: MessageSquare,
    title: 'Belum ada chat',
    body: 'Pelanggan akan muncul di sini bila mereka mula bual dengan kedai anda.',
  },
  'no-match': {
    icon: SearchX,
    title: 'Tiada hasil',
    body: 'Tiada chat menepati pencarian anda. Cuba tukar tab atau padam carian.',
  },
  'no-selection': {
    icon: MousePointerClick,
    title: 'Pilih chat di sebelah',
    body: 'Pilih satu perbualan dari senarai untuk mula balas pelanggan.',
  },
};

export default function EmptyState({ variant, stats, className = '' }: Props) {
  const { icon: Icon, title, body } = COPY[variant];
  return (
    <div
      className={`h-full w-full flex items-center justify-center p-6 ${className}`}
    >
      <div className="text-center max-w-md">
        <div className="mx-auto mb-3 inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-white/[0.04] ring-1 ring-white/[0.08] text-white/40">
          <Icon size={20} strokeWidth={1.5} />
        </div>
        <div className="font-geist text-sm font-medium text-white/80 mb-1">
          {title}
        </div>
        <div className="font-geist text-xs text-white/40 leading-relaxed">
          {body}
        </div>

        {stats && stats.length > 0 && (
          <div className="mt-6 grid grid-cols-3 gap-2">
            {stats.map((s) => (
              <div
                key={s.label}
                className="rounded-xl bg-white/[0.02] ring-1 ring-white/[0.06] px-3 py-3"
              >
                <div
                  className={[
                    'font-mono font-semibold text-lg',
                    s.tone === 'accent'
                      ? 'text-[#C7FF3D]'
                      : s.tone === 'alert'
                        ? 'text-amber-300'
                        : 'text-white',
                  ].join(' ')}
                >
                  {s.value}
                </div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-white/40 mt-1">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

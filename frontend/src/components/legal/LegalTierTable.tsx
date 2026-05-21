import React from 'react';
import { Check } from 'lucide-react';
import type { TierRow } from '@/lib/legal/terms-content-bm';

type Props = {
  rows: TierRow[];
  labels?: {
    caption: string;
  };
};

const DEFAULT_LABELS = {
  caption: 'Subscription plan tiers, prices, and features.',
};

/**
 * Renders the Terms section 4.1 tier table (4 rows: Free / Starter /
 * Basic / Pro).
 *
 * Rather than a traditional row-per-tier table, this is laid out as a
 * comparison grid — one card per tier on desktop, stacked on mobile,
 * with the features rendered as a bullet checklist. Tier names get a
 * coloured accent (Free = ink, Starter = info, Basic = brand, Pro =
 * volt) so they're visually distinguishable.
 *
 * Each feature line is a plain string from the content file (no
 * markdown parsing needed) — we render with a Check icon prefix.
 */
export function LegalTierTable({ rows, labels: l = DEFAULT_LABELS }: Props) {
  return (
    <div
      className="my-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      role="table"
      aria-label={l.caption}
    >
      {rows.map((row) => {
        const accent = TIER_ACCENTS[row.tier] ?? TIER_ACCENTS.default;
        return (
          <div
            key={row.tier}
            role="row"
            className={`rounded-xl border ${accent.border} ${accent.bg} p-5 flex flex-col`}
          >
            <div className="mb-4">
              <h4 className={`text-lg font-bold ${accent.text}`}>{row.tier}</h4>
              <p className="text-sm text-ink-600 mt-0.5">{row.price}</p>
            </div>
            <ul className="space-y-2 text-sm text-ink-700">
              {row.features.map((feature, j) => (
                <li key={j} className="flex items-start gap-2">
                  <Check
                    className={`h-4 w-4 mt-0.5 shrink-0 ${accent.iconText}`}
                    aria-hidden="true"
                  />
                  <span className="leading-relaxed">{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

const TIER_ACCENTS: Record<string, { border: string; bg: string; text: string; iconText: string }> = {
  Free: {
    border: 'border-ink-200',
    bg: 'bg-white',
    text: 'text-ink-900',
    iconText: 'text-ink-400',
  },
  Starter: {
    border: 'border-info-400/30',
    bg: 'bg-white',
    text: 'text-info-500',
    iconText: 'text-info-400',
  },
  Basic: {
    border: 'border-brand-200',
    bg: 'bg-brand-50/40',
    text: 'text-brand-700',
    iconText: 'text-brand-500',
  },
  Pro: {
    border: 'border-volt-500',
    bg: 'bg-volt-100/30',
    text: 'text-volt-600',
    iconText: 'text-volt-600',
  },
  default: {
    border: 'border-ink-200',
    bg: 'bg-white',
    text: 'text-ink-900',
    iconText: 'text-ink-400',
  },
};

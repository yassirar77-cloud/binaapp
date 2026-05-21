import React from 'react';
import type { QuotaRow } from '@/lib/legal/terms-content-bm';

type Props = {
  rows: QuotaRow[];
  labels?: {
    limitType: string;
    caption: string;
  };
};

const DEFAULT_LABELS = {
  limitType: 'Limit',
  caption: 'Quota limits per subscription tier.',
};

/**
 * Renders the Terms section 4.5 quota table — a 6-row × 5-column
 * matrix (6 limit types × Free / Starter / Basic / Pro).
 *
 * Header row uses the same tier accent colours as LegalTierTable so
 * users can pattern-match plans across the two tables. The
 * "Unlimited" / "Tanpa had" string values get a subtle emphasis
 * so the unconstrained cells are easy to scan.
 *
 * Horizontal scroll on mobile — the matrix needs all five columns
 * adjacent to be comparable.
 */
export function LegalQuotaTable({ rows, labels: l = DEFAULT_LABELS }: Props) {
  return (
    <div className="my-6 -mx-4 sm:mx-0 overflow-x-auto rounded-xl border border-ink-200 bg-white">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{l.caption}</caption>
        <thead className="bg-ink-050 text-ink-700">
          <tr>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.limitType}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold text-ink-700">Free</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold text-info-500">Starter</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold text-brand-700">Basic</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold text-volt-600">Pro</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {rows.map((row, idx) => (
            <tr key={idx} className="hover:bg-ink-050/60">
              <th scope="row" className="px-4 py-3 text-left font-medium text-ink-900">
                {row.limitType}
              </th>
              <td className="px-4 py-3 text-ink-700">{formatQuota(row.free)}</td>
              <td className="px-4 py-3 text-ink-700">{formatQuota(row.starter)}</td>
              <td className="px-4 py-3 text-ink-700">{formatQuota(row.basic)}</td>
              <td className="px-4 py-3 text-ink-700">{formatQuota(row.pro)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Highlight "Unlimited" / "Tanpa had" cells with a subtle pill so the
// visual scan picks out unconstrained tiers without parsing every cell.
function formatQuota(value: string): React.ReactNode {
  if (/^(unlimited|tanpa had)$/i.test(value.trim())) {
    return (
      <span className="inline-flex items-center rounded-full bg-volt-100 px-2 py-0.5 text-xs font-medium text-volt-600">
        ∞ {value}
      </span>
    );
  }
  return value;
}

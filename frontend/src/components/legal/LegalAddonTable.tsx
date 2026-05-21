import React from 'react';
import type { AddonRow } from '@/lib/legal/terms-content-bm';

type Props = {
  rows: AddonRow[];
  labels?: {
    addonType: string;
    price: string;
    expiry: string;
    refundPolicy: string;
    caption: string;
  };
};

const DEFAULT_LABELS = {
  addonType: 'Addon Type',
  price: 'Price',
  expiry: 'Validity',
  refundPolicy: 'Refund Policy',
  caption: 'Addons available for purchase, pricing, validity, and refund policy.',
};

/**
 * Renders the Terms section 4.4 addon table (5 rows: ai_image,
 * ai_hero, website, rider, zone).
 *
 * Four columns — fits cleanly on desktop, scrolls on mobile. The
 * refundPolicy strings contain a "•" separator that visually breaks
 * the policy into two clauses (unused / used); we render them as a
 * single cell rather than splitting columns to keep the table compact.
 */
export function LegalAddonTable({ rows, labels: l = DEFAULT_LABELS }: Props) {
  return (
    <div className="my-6 -mx-4 sm:mx-0 overflow-x-auto rounded-xl border border-ink-200 bg-white">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{l.caption}</caption>
        <thead className="bg-ink-050 text-ink-700">
          <tr>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.addonType}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold whitespace-nowrap">{l.price}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold whitespace-nowrap">{l.expiry}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.refundPolicy}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {rows.map((row, idx) => (
            <tr key={idx} className="hover:bg-ink-050/60">
              <td className="px-4 py-3 font-medium text-ink-900">{row.addonType}</td>
              <td className="px-4 py-3 text-ink-700 whitespace-nowrap font-geist-mono text-[0.95em]">
                {row.price}
              </td>
              <td className="px-4 py-3 text-ink-600 whitespace-nowrap">{row.expiry}</td>
              <td className="px-4 py-3 text-ink-600 leading-relaxed">{row.refundPolicy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

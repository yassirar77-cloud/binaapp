import React from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import type { AIVendorRow } from '@/lib/legal/policy-content-bm';

type Props = {
  rows: AIVendorRow[];
  /** Locale-specific column headers. Defaults are English. */
  labels?: {
    feature: string;
    vendor: string;
    region: string;
    dataSent: string;
    piiRisk: string;
    consentStatus: string;
    riskWarning: string;
    riskSafe: string;
    caption: string;
  };
};

const DEFAULT_LABELS = {
  feature: 'Feature',
  vendor: 'Provider',
  region: 'Region',
  dataSent: 'Data Sent',
  piiRisk: 'PII Risk',
  consentStatus: 'Consent Status',
  riskWarning: 'PII risk',
  riskSafe: 'No PII',
  caption: 'AI providers, regions, data sent, PII risk, and consent status by feature.',
};

/**
 * Renders the Privacy Policy section 6 AI vendor table (8 rows).
 *
 * Horizontal scroll on small screens — the table has 6 columns and
 * forcing it to wrap into cards on mobile loses the row-to-row
 * comparison that makes the disclosure useful. On <sm screens users
 * scroll the table horizontally inside its container.
 *
 * Each row has a tooltip-style PII risk indicator (warning icon for
 * `warning`, shield icon for `safe`) so the visual scan picks out
 * high-risk vendor calls at a glance.
 */
export function LegalAIVendorTable({ rows, labels: l = DEFAULT_LABELS }: Props) {
  return (
    <div className="my-6 -mx-4 sm:mx-0 overflow-x-auto rounded-xl border border-ink-200 bg-white">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{l.caption}</caption>
        <thead className="bg-ink-050 text-ink-700">
          <tr>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.feature}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.vendor}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.region}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.dataSent}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.piiRisk}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.consentStatus}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {rows.map((row, idx) => (
            <tr key={idx} className="align-top hover:bg-ink-050/60">
              <td className="px-4 py-3 font-medium text-ink-900">{row.feature}</td>
              <td className="px-4 py-3 text-ink-700">{row.vendor}</td>
              <td className="px-4 py-3 text-ink-600 whitespace-nowrap">{row.region}</td>
              <td className="px-4 py-3 text-ink-600 leading-relaxed">{row.dataSent}</td>
              <td className="px-4 py-3">
                {row.piiRisk === 'warning' ? (
                  <span className="inline-flex items-start gap-1.5 text-warn-500">
                    <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" aria-hidden="true" />
                    <span className="text-xs leading-relaxed">
                      <span className="sr-only">{l.riskWarning}: </span>
                      {row.piiNote}
                    </span>
                  </span>
                ) : (
                  <span className="inline-flex items-start gap-1.5 text-ok-500">
                    <ShieldCheck className="h-4 w-4 mt-0.5 shrink-0" aria-hidden="true" />
                    <span className="text-xs leading-relaxed">
                      <span className="sr-only">{l.riskSafe}: </span>
                      {row.piiNote}
                    </span>
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-ink-600 text-xs leading-relaxed">{row.consentStatus}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

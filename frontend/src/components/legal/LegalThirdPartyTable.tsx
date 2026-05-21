import React from 'react';
import { ExternalLink } from 'lucide-react';
import type { ThirdPartyRow } from '@/lib/legal/terms-content-bm';

type Props = {
  rows: ThirdPartyRow[];
  labels?: {
    service: string;
    region: string;
    purpose: string;
    policy: string;
    policyLinkText: string;
    caption: string;
  };
};

const DEFAULT_LABELS = {
  service: 'Service',
  region: 'Region',
  purpose: 'Purpose',
  policy: 'Privacy Policy',
  policyLinkText: 'View',
  caption: 'Third-party service providers, regions, purposes, and links to their privacy policies.',
};

/**
 * Renders the Terms section 17 third-party services table (8 rows:
 * ToyyibPay, Supabase, Render, Vercel, Stability AI, DeepSeek,
 * Qwen/Alibaba Cloud, Anthropic Claude).
 *
 * Service names and policy URLs are passed through unchanged — they're
 * vendor proper nouns and stable URLs that don't translate. Each
 * policy URL opens in a new tab with rel="noopener noreferrer" so the
 * vendor site can't reach back to ours via window.opener.
 */
export function LegalThirdPartyTable({ rows, labels: l = DEFAULT_LABELS }: Props) {
  return (
    <div className="my-6 -mx-4 sm:mx-0 overflow-x-auto rounded-xl border border-ink-200 bg-white">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{l.caption}</caption>
        <thead className="bg-ink-050 text-ink-700">
          <tr>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.service}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.region}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.purpose}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold whitespace-nowrap">
              {l.policy}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {rows.map((row, idx) => (
            <tr key={idx} className="hover:bg-ink-050/60">
              <td className="px-4 py-3 font-medium text-ink-900 whitespace-nowrap">{row.service}</td>
              <td className="px-4 py-3 text-ink-600 whitespace-nowrap">{row.region}</td>
              <td className="px-4 py-3 text-ink-600 leading-relaxed">{row.purpose}</td>
              <td className="px-4 py-3 whitespace-nowrap">
                <a
                  href={row.policyUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-brand-500 hover:text-brand-600 underline underline-offset-2"
                >
                  {l.policyLinkText}
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

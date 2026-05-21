import React from 'react';
import type { RetentionRow } from '@/lib/legal/policy-content-bm';

type Props = {
  rows: RetentionRow[];
  labels?: {
    dataType: string;
    period: string;
    caption: string;
  };
};

const DEFAULT_LABELS = {
  dataType: 'Data Type',
  period: 'Retention Period',
  caption: 'Data retention periods by data type.',
};

/**
 * Renders the Privacy Policy section 14 retention table (12 rows).
 *
 * Two columns only, so this fits comfortably on mobile without
 * horizontal scrolling. The `dataType` column may contain inline code
 * spans (e.g. `bina_visitor`) — those are pre-formatted text from the
 * content file; we pass them through verbatim and the renderer in
 * LegalMarkdown style is applied via the CSS class on the cell.
 *
 * Note: this component does not parse markdown inside cells. The
 * BM/EN content files use backtick-style code in `dataType` strings
 * for the localStorage key; we render those with a font-mono class
 * on the cell so they look like inline code without requiring full
 * markdown rendering in a table cell.
 */
export function LegalRetentionTable({ rows, labels: l = DEFAULT_LABELS }: Props) {
  return (
    <div className="my-6 overflow-hidden rounded-xl border border-ink-200 bg-white">
      <table className="min-w-full text-sm">
        <caption className="sr-only">{l.caption}</caption>
        <thead className="bg-ink-050 text-ink-700">
          <tr>
            <th scope="col" className="px-4 py-3 text-left font-semibold w-1/2">{l.dataType}</th>
            <th scope="col" className="px-4 py-3 text-left font-semibold">{l.period}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {rows.map((row, idx) => (
            <tr key={idx} className="hover:bg-ink-050/60">
              <td className="px-4 py-3 font-medium text-ink-900 [&_code]:font-geist-mono">
                {renderWithInlineCode(row.dataType)}
              </td>
              <td className="px-4 py-3 text-ink-700 leading-relaxed">{row.period}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Minimal inline-code parser scoped to the retention table — only handles
// backtick segments so cells like `bina_visitor` render as monospace.
function renderWithInlineCode(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /`([^`]+)`/g;
  let lastIndex = 0;
  let key = 0;
  let m: RegExpExecArray | null;

  while ((m = re.exec(text)) !== null) {
    if (m.index > lastIndex) {
      parts.push(text.slice(lastIndex, m.index));
    }
    parts.push(
      <code
        key={key++}
        className="px-1.5 py-0.5 rounded bg-ink-100 text-ink-800 text-[0.875em]"
      >
        {m[1]}
      </code>,
    );
    lastIndex = m.index + m[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, History } from 'lucide-react';
import type { ChangelogEntry } from '@/lib/legal/policy-content-bm';

type Props = {
  entries: ChangelogEntry[];
  title: string;
  labels?: {
    showAll: string;
    hideOlder: string;
    versionLabel: string;
  };
};

const DEFAULT_LABELS = {
  showAll: 'Show all versions',
  hideOlder: 'Hide older versions',
  versionLabel: 'Version',
};

/**
 * Collapsible changelog renderer. Latest version is always expanded;
 * older versions are collapsed by default behind a "Show all versions"
 * toggle so the doc footer doesn't fill up with the v1.0 / v2.0
 * historical entries every time someone scrolls to the bottom.
 *
 * Lives behind 'use client' for the collapse state — it's the only
 * piece of interactivity in the changelog. If JS fails to load, all
 * entries render expanded as a graceful degradation (the initial state
 * is 'closed' but the markup is fully present — screen readers and
 * search engines see every entry).
 */
export function LegalChangelog({ entries, title, labels: l = DEFAULT_LABELS }: Props) {
  const [showOlder, setShowOlder] = useState(false);
  const [latest, ...older] = entries;
  const hasOlder = older.length > 0;

  return (
    <section
      id="riwayat-perubahan"
      className="mt-16 rounded-2xl border border-ink-200 bg-white p-6"
      aria-labelledby="changelog-heading"
    >
      <h2
        id="changelog-heading"
        className="flex items-center gap-2 text-xl font-semibold text-ink-900 mb-4"
      >
        <History className="h-5 w-5 text-ink-400" aria-hidden="true" />
        {title}
      </h2>

      {latest && <ChangelogVersion entry={latest} highlight versionLabel={l.versionLabel} />}

      {hasOlder && (
        <>
          {/* Older versions are always in the DOM (screen readers, print,
              and search engines see them) but hidden by default on screen
              behind the toggle. `print:block` ensures the printed PDF
              shows the full version history regardless of toggle state. */}
          <div
            id="changelog-older"
            className={`mt-6 pt-6 border-t border-ink-100 space-y-6 ${showOlder ? '' : 'hidden'} print:block`}
          >
            {older.map((entry) => (
              <ChangelogVersion
                key={entry.version}
                entry={entry}
                highlight={false}
                versionLabel={l.versionLabel}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={() => setShowOlder((v) => !v)}
            className="mt-4 inline-flex items-center gap-1.5 text-sm text-brand-500 hover:text-brand-600 font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-1 rounded print:hidden"
            aria-expanded={showOlder}
            aria-controls="changelog-older"
          >
            {showOlder ? (
              <ChevronDown className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            )}
            {showOlder ? l.hideOlder : l.showAll}
          </button>
        </>
      )}
    </section>
  );
}

function ChangelogVersion({
  entry,
  highlight,
  versionLabel,
}: {
  entry: ChangelogEntry;
  highlight: boolean;
  versionLabel: string;
}) {
  return (
    <div>
      <div className="flex items-baseline gap-3 mb-3">
        <span
          className={
            highlight
              ? 'inline-flex items-center rounded-full bg-brand-500 px-2.5 py-0.5 text-xs font-semibold text-white'
              : 'inline-flex items-center rounded-full bg-ink-100 px-2.5 py-0.5 text-xs font-medium text-ink-600'
          }
          aria-label={`${versionLabel} ${entry.version}`}
        >
          v{entry.version}
        </span>
        <span className="text-sm text-ink-500">{entry.date}</span>
      </div>
      <ul className="space-y-1.5 text-sm text-ink-600 list-disc pl-6 marker:text-ink-300">
        {entry.changes.map((change, i) => (
          <li key={i} className="leading-relaxed">
            {change}
          </li>
        ))}
      </ul>
    </div>
  );
}

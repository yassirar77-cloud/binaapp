import React from 'react';
import { Calendar, Clock, FileText } from 'lucide-react';

type Props = {
  version: string;
  effectiveDate: string;
  lastUpdated: string;
  estimatedReadingMinutes: number;
  /** Localized label override — "min baca" in BM, "min read" in EN. */
  readingTimeLabel?: string;
  effectiveDateLabel?: string;
  lastUpdatedLabel?: string;
  versionLabel?: string;
};

/**
 * Top-of-document metadata pills: version badge, effective date, last
 * updated, estimated reading time. Sits below the document title in
 * LegalDocument and renders the same in both BM and EN — the label
 * strings are passed through so the calling route can pick the
 * language-appropriate copy.
 */
export function LegalMetadata({
  version,
  effectiveDate,
  lastUpdated,
  estimatedReadingMinutes,
  readingTimeLabel = 'min read',
  effectiveDateLabel = 'Effective',
  lastUpdatedLabel = 'Updated',
  versionLabel = 'Version',
}: Props) {
  return (
    <dl className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink-500">
      <div className="flex items-center gap-2">
        <span
          className="inline-flex items-center rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700"
          aria-label={`${versionLabel} ${version}`}
        >
          v{version}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <Calendar className="h-4 w-4 text-ink-400" aria-hidden="true" />
        <dt className="sr-only">{effectiveDateLabel}</dt>
        <dd>
          <span className="text-ink-400">{effectiveDateLabel}:</span>{' '}
          <span className="text-ink-700 font-medium">{effectiveDate}</span>
        </dd>
      </div>
      {lastUpdated !== effectiveDate && (
        <div className="flex items-center gap-1.5">
          <FileText className="h-4 w-4 text-ink-400" aria-hidden="true" />
          <dt className="sr-only">{lastUpdatedLabel}</dt>
          <dd>
            <span className="text-ink-400">{lastUpdatedLabel}:</span>{' '}
            <span className="text-ink-700 font-medium">{lastUpdated}</span>
          </dd>
        </div>
      )}
      <div className="flex items-center gap-1.5">
        <Clock className="h-4 w-4 text-ink-400" aria-hidden="true" />
        <dt className="sr-only">{readingTimeLabel}</dt>
        <dd className="text-ink-700 font-medium">
          {estimatedReadingMinutes} {readingTimeLabel}
        </dd>
      </div>
    </dl>
  );
}

import React from 'react';
import type { PrivacyPolicy } from '@/lib/legal/policy-content-bm';
import type { TermsOfService } from '@/lib/legal/terms-content-bm';
import { LegalMarkdown } from './LegalMarkdown';
import { LegalMetadata } from './LegalMetadata';
import { LegalSection } from './LegalSection';

type Language = 'bm' | 'en';

type LegalDocumentProps = {
  doc: PrivacyPolicy | TermsOfService;
  docType: 'privacy' | 'terms';
  language: Language;
  /** Page title shown as the h1. Step 3f passes the route-appropriate
   *  string ("Polisi Privasi BinaApp" / "BinaApp Privacy Policy" / …). */
  documentTitle: string;
  /** Optional language toggle slot, populated in commit 3. */
  languageToggle?: React.ReactNode;
  /** Optional TOC slot, populated in commit 3. */
  toc?: React.ReactNode;
  /** Optional changelog slot, populated in commit 2. */
  changelog?: React.ReactNode;
};

/**
 * Top-level wrapper for a legal document. Accepts a PrivacyPolicy or
 * TermsOfService value (from frontend/src/lib/legal/*) and renders the
 * full structure: header with metadata, executive summary, optional
 * business-model callout (Terms only), introduction, numbered sections,
 * changelog slot, and footer with prevailing-language clause + contact.
 *
 * Composition slots (languageToggle, toc, changelog) are accepted as
 * props so the interactive client components can be injected from the
 * route in Step 3f without forcing this server component to ship JS.
 *
 * The doc-vs-route discrimination (`docType` + `language`) controls the
 * label strings that don't live in the content files — "min read",
 * "Effective", section labels in metadata, etc.
 */
export function LegalDocument({
  doc,
  docType,
  language,
  documentTitle,
  languageToggle,
  toc,
  changelog,
}: LegalDocumentProps) {
  const labels = LABELS[language];
  const hasBusinessModelCallout =
    docType === 'terms' && 'businessModelCallout' in doc;

  return (
    <div className="bg-ink-050 min-h-screen scroll-smooth print:bg-white">
      {/* Skip to content link for keyboard users */}
      <a
        href="#legal-main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-brand-500 focus:px-3 focus:py-2 focus:text-sm focus:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
      >
        {labels.skipToContent}
      </a>

      <article className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 lg:py-12 print:max-w-none print:py-4">
        <header className="mx-auto max-w-3xl">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
            <h1 className="text-3xl sm:text-4xl font-bold text-ink-900 tracking-tight">
              {documentTitle}
            </h1>
            {languageToggle && <div className="shrink-0">{languageToggle}</div>}
          </div>
          <LegalMetadata
            version={doc.version}
            effectiveDate={doc.effectiveDate}
            lastUpdated={doc.lastUpdated}
            estimatedReadingMinutes={doc.estimatedReadingMinutes}
            readingTimeLabel={labels.readingTime}
            effectiveDateLabel={labels.effective}
            lastUpdatedLabel={labels.updated}
            versionLabel={labels.version}
          />
        </header>

        <div className="mt-10 grid grid-cols-1 lg:grid-cols-[1fr_18rem] gap-8 lg:gap-12 print:block">
          <main id="legal-main" className="mx-auto w-full max-w-3xl lg:mx-0 print:max-w-none">
            {/* Executive summary callout */}
            <section
              id="ringkasan"
              className="rounded-2xl border border-brand-100 bg-brand-50/40 p-6 mb-10"
              aria-labelledby="ringkasan-heading"
            >
              <h2
                id="ringkasan-heading"
                className="text-lg font-semibold text-brand-700 mb-3"
              >
                {doc.executiveSummary.title}
              </h2>
              <LegalMarkdown content={doc.executiveSummary.content} />
            </section>

            {/* Business model callout — Terms of Service only */}
            {hasBusinessModelCallout && (
              <section
                id="model-perniagaan"
                className="rounded-2xl border-l-4 border-warn-400 bg-warn-50/50 p-6 mb-10"
                aria-labelledby="model-perniagaan-heading"
              >
                <h2
                  id="model-perniagaan-heading"
                  className="text-lg font-semibold text-ink-900 mb-3"
                >
                  {(doc as TermsOfService).businessModelCallout.title}
                </h2>
                <LegalMarkdown
                  content={(doc as TermsOfService).businessModelCallout.content}
                />
              </section>
            )}

            {/* Introduction (numbered as section 1 in source content) */}
            <section
              id="pengenalan"
              className="mb-10"
              aria-labelledby="pengenalan-heading"
            >
              <h2
                id="pengenalan-heading"
                className="text-2xl font-semibold text-ink-900 mb-4"
              >
                {doc.introduction.title}
              </h2>
              <LegalMarkdown content={doc.introduction.content} />
            </section>

            {/* Numbered sections 2–N */}
            {doc.sections.map((section) => (
              <LegalSection key={section.id} section={section} />
            ))}

            {/* Changelog slot — rendered in commit 2 */}
            {changelog}

            {/* Document footer: prevailing language reminder + contact */}
            <footer
              className="mt-16 border-t border-ink-200 pt-8"
              aria-label={labels.documentFooter}
            >
              <div className="rounded-xl bg-ink-100 p-5">
                <h3 className="text-sm font-semibold text-ink-900 mb-2">
                  {doc.prevailingLanguage.title}
                </h3>
                <p className="text-sm text-ink-600 leading-relaxed">
                  {doc.prevailingLanguage.content}
                </p>
              </div>

              <div className="mt-6 text-sm text-ink-500 space-y-1">
                <p>
                  <span className="font-medium text-ink-700">{doc.contact.company}</span>
                  {' · '}SSM {doc.contact.ssm}
                </p>
                <p>
                  {labels.dpoLabel}:{' '}
                  <a
                    href={`mailto:${doc.contact.dpoEmail}`}
                    className="text-brand-500 hover:text-brand-600 underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-1 rounded-sm"
                  >
                    {doc.contact.dpoEmail}
                  </a>
                </p>
              </div>
            </footer>
          </main>

          {/* TOC sidebar slot — interactive client component injected
              by the page route (LegalTOC). Hidden in print output so the
              PDF/printed page is a single column of pure content. */}
          {toc && (
            <aside
              className="hidden lg:block print:hidden"
              aria-label={labels.tocAriaLabel}
            >
              <div className="sticky top-8">{toc}</div>
            </aside>
          )}
        </div>
      </article>
    </div>
  );
}

const LABELS = {
  bm: {
    skipToContent: 'Lompat ke kandungan utama',
    readingTime: 'min baca',
    effective: 'Berkuat kuasa',
    updated: 'Dikemas kini',
    version: 'Versi',
    documentFooter: 'Bahagian akhir dokumen',
    tocAriaLabel: 'Senarai kandungan',
    dpoLabel: 'Pegawai Perlindungan Data',
  },
  en: {
    skipToContent: 'Skip to main content',
    readingTime: 'min read',
    effective: 'Effective',
    updated: 'Updated',
    version: 'Version',
    documentFooter: 'End of document',
    tocAriaLabel: 'Table of contents',
    dpoLabel: 'Data Protection Officer',
  },
} as const;

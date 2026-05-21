import React from 'react';
import type { PolicySection } from '@/lib/legal/policy-content-bm';
import type { TermsSection } from '@/lib/legal/terms-content-bm';
import { LegalMarkdown } from './LegalMarkdown';

type LegalSectionProps = {
  section: PolicySection | TermsSection;
};

/**
 * Renders one numbered section of a legal document: anchored heading,
 * narrative content (via LegalMarkdown), and any structured tables
 * attached to the section. Table rendering is added in commit 2 — for
 * now this component only handles the section title and prose so the
 * base document layout can land first.
 *
 * The `id` on the wrapping <section> is the same string used in the
 * BM source-of-truth file so URL anchors like /polisi-privasi#ai-features
 * jump to the right place in both languages.
 */
export function LegalSection({ section }: LegalSectionProps) {
  return (
    <section
      id={section.id}
      className="scroll-mt-24"
      aria-labelledby={`${section.id}-heading`}
    >
      <h2
        id={`${section.id}-heading`}
        className="group flex items-baseline gap-2 text-2xl font-semibold text-ink-900 mt-12 mb-4 first:mt-0"
      >
        <a
          href={`#${section.id}`}
          className="no-underline hover:underline decoration-brand-300 underline-offset-4"
          aria-label={`Pautan ke seksyen: ${section.title}`}
        >
          {section.title}
        </a>
      </h2>
      <LegalMarkdown content={section.content} />
      {/* Tables (aiVendorTable, retentionTable, tierTable, addonTable,
          quotaTable, thirdPartyTable) are rendered in commit 2 once
          the dedicated table components land. */}
    </section>
  );
}

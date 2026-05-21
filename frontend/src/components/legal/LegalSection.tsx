import React from 'react';
import type { PolicySection } from '@/lib/legal/policy-content-bm';
import type { TermsSection } from '@/lib/legal/terms-content-bm';
import { LegalMarkdown } from './LegalMarkdown';
import { LegalAIVendorTable } from './LegalAIVendorTable';
import { LegalRetentionTable } from './LegalRetentionTable';
import { LegalTierTable } from './LegalTierTable';
import { LegalAddonTable } from './LegalAddonTable';
import { LegalQuotaTable } from './LegalQuotaTable';
import { LegalThirdPartyTable } from './LegalThirdPartyTable';

type LegalSectionProps = {
  section: PolicySection | TermsSection;
  /** Localized anchor-link aria-label, e.g. "Link to section:" / "Pautan ke seksyen:". */
  anchorLabelPrefix?: string;
};

/**
 * Renders one numbered section of a legal document: anchored heading,
 * narrative content (via LegalMarkdown), and any structured tables
 * attached to the section.
 *
 * The `id` on the wrapping <section> is the same string used in the
 * BM source-of-truth file so URL anchors like /polisi-privasi#ai-features
 * jump to the right place in both languages.
 *
 * Tables are detected with `in` checks — both PolicySection and
 * TermsSection are unions of optional table fields, so TypeScript
 * needs the guard to narrow before accessing each one.
 */
export function LegalSection({
  section,
  anchorLabelPrefix = 'Link to section:',
}: LegalSectionProps) {
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
          className="no-underline hover:underline decoration-brand-300 underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 rounded print:no-underline"
          aria-label={`${anchorLabelPrefix} ${section.title}`}
        >
          {section.title}
        </a>
      </h2>
      <LegalMarkdown content={section.content} />

      {/* PolicySection-shaped tables */}
      {'aiVendorTable' in section && section.aiVendorTable && (
        <LegalAIVendorTable rows={section.aiVendorTable} />
      )}
      {'retentionTable' in section && section.retentionTable && (
        <LegalRetentionTable rows={section.retentionTable} />
      )}

      {/* TermsSection-shaped tables */}
      {'tierTable' in section && section.tierTable && (
        <LegalTierTable rows={section.tierTable} />
      )}
      {'addonTable' in section && section.addonTable && (
        <LegalAddonTable rows={section.addonTable} />
      )}
      {'quotaTable' in section && section.quotaTable && (
        <LegalQuotaTable rows={section.quotaTable} />
      )}
      {'thirdPartyTable' in section && section.thirdPartyTable && (
        <LegalThirdPartyTable rows={section.thirdPartyTable} />
      )}
    </section>
  );
}

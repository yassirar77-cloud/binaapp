import type { Metadata } from 'next';
import {
  LegalDocument,
  LegalLanguageToggle,
  LegalTOC,
  LegalChangelog,
  type TOCItem,
} from '@/components/legal';
import { termsEN } from '@/lib/legal/terms-content-en';

export const metadata: Metadata = {
  title: 'Terms of Service | BinaApp',
  description:
    'BinaApp Terms of Service v3.0 — subscription plans, addons, quotas, intellectual property rights, limitation of liability, and governing law.',
  alternates: {
    canonical: '/terms-of-service',
    languages: {
      'ms-MY': '/terma-perkhidmatan',
      en: '/terms-of-service',
    },
  },
  openGraph: {
    title: 'BinaApp Terms of Service v3.0',
    description: 'Terms of use for the BinaApp platform for F&B merchants in Malaysia.',
    locale: 'en_US',
    type: 'article',
  },
  robots: { index: true, follow: true },
};

const TOC_ITEMS: TOCItem[] = [
  { id: 'ringkasan', title: termsEN.executiveSummary.title },
  { id: 'model-perniagaan', title: termsEN.businessModelCallout.title },
  { id: 'pengenalan', title: termsEN.introduction.title },
  ...termsEN.sections.map((s) => ({ id: s.id, title: s.title })),
  { id: 'riwayat-perubahan', title: 'Version History' },
];

/**
 * EN route wrapper. See note on PrivacyPolicyPage about the `lang="en"`
 * wrapper div — same reasoning applies here: root layout has
 * <html lang="ms"> and we switch the language attribute via nesting
 * for screen-reader pronunciation, since cross-route overrides of
 * <html lang> require route groups.
 */
export default function TermsOfServicePage() {
  return (
    <div lang="en">
      <LegalDocument
        doc={termsEN}
        docType="terms"
        language="en"
        documentTitle="BinaApp Terms of Service"
        languageToggle={
          <LegalLanguageToggle
            current="en"
            bmHref="/terma-perkhidmatan"
            enHref="/terms-of-service"
            ariaLabel="Switch language"
          />
        }
        toc={
          <LegalTOC
            items={TOC_ITEMS}
            label="Table of Contents"
            mobileLabels={{
              open: 'Open table of contents',
              close: 'Close table of contents',
            }}
          />
        }
        changelog={
          <LegalChangelog
            entries={termsEN.changelog}
            title="Version History"
            labels={{
              showAll: 'Show all versions',
              hideOlder: 'Hide older versions',
              versionLabel: 'Version',
            }}
          />
        }
      />
    </div>
  );
}

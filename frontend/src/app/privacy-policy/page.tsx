import type { Metadata } from 'next';
import {
  LegalDocument,
  LegalLanguageToggle,
  LegalTOC,
  LegalChangelog,
  type TOCItem,
} from '@/components/legal';
import { privacyPolicyEN } from '@/lib/legal/policy-content-en';

export const metadata: Metadata = {
  title: 'Privacy Policy | BinaApp',
  description:
    'BinaApp Privacy Policy v3.0 — how we collect, use, and protect your personal data under the Personal Data Protection Act 2010.',
  alternates: {
    canonical: '/privacy-policy',
    languages: {
      'ms-MY': '/polisi-privasi',
      en: '/privacy-policy',
    },
  },
  openGraph: {
    title: 'BinaApp Privacy Policy v3.0',
    description: 'How we collect, use, and protect your personal data.',
    locale: 'en_US',
    type: 'article',
  },
  robots: { index: true, follow: true },
};

const TOC_ITEMS: TOCItem[] = [
  { id: 'ringkasan', title: privacyPolicyEN.executiveSummary.title },
  { id: 'pengenalan', title: privacyPolicyEN.introduction.title },
  ...privacyPolicyEN.sections.map((s) => ({ id: s.id, title: s.title })),
  { id: 'riwayat-perubahan', title: 'Version History' },
];

/**
 * EN route wrapper. The page content sits inside <div lang="en"> so
 * screen readers switch pronunciation rules for English text — the
 * root layout sets <html lang="ms"> and Next.js' App Router doesn't
 * let nested routes override that attribute without route groups +
 * parallel layouts (too invasive for this PR). The `lang` attribute
 * on any ancestor element is honoured per WCAG SC 3.1.2.
 */
export default function PrivacyPolicyPage() {
  return (
    <div lang="en">
      <LegalDocument
        doc={privacyPolicyEN}
        docType="privacy"
        language="en"
        documentTitle="BinaApp Privacy Policy"
        languageToggle={
          <LegalLanguageToggle
            current="en"
            bmHref="/polisi-privasi"
            enHref="/privacy-policy"
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
            entries={privacyPolicyEN.changelog}
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

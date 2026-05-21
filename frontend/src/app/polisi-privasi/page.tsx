import type { Metadata } from 'next';
import {
  LegalDocument,
  LegalLanguageToggle,
  LegalTOC,
  LegalChangelog,
  type TOCItem,
} from '@/components/legal';
import { privacyPolicyBM } from '@/lib/legal/policy-content-bm';

export const metadata: Metadata = {
  title: 'Polisi Privasi | BinaApp',
  description:
    'Polisi Privasi BinaApp v3.0 — bagaimana kami mengumpul, menggunakan, dan melindungi data peribadi anda di bawah Akta Perlindungan Data Peribadi 2010.',
  alternates: {
    canonical: '/polisi-privasi',
    languages: {
      'ms-MY': '/polisi-privasi',
      en: '/privacy-policy',
    },
  },
  openGraph: {
    title: 'Polisi Privasi BinaApp v3.0',
    description:
      'Bagaimana kami mengumpul, menggunakan, dan melindungi data peribadi anda.',
    locale: 'ms_MY',
    type: 'article',
  },
  robots: { index: true, follow: true },
};

// TOC items combine the non-numbered anchors (executive summary, intro,
// changelog) with the 24 numbered sections from the content file, in
// document order. Building this once outside the component keeps the
// render server-cheap.
const TOC_ITEMS: TOCItem[] = [
  { id: 'ringkasan', title: privacyPolicyBM.executiveSummary.title },
  { id: 'pengenalan', title: privacyPolicyBM.introduction.title },
  ...privacyPolicyBM.sections.map((s) => ({ id: s.id, title: s.title })),
  { id: 'riwayat-perubahan', title: 'Riwayat Perubahan' },
];

export default function PolisiPrivasiPage() {
  return (
    <LegalDocument
      doc={privacyPolicyBM}
      docType="privacy"
      language="bm"
      documentTitle="Polisi Privasi BinaApp"
      languageToggle={
        <LegalLanguageToggle
          current="bm"
          bmHref="/polisi-privasi"
          enHref="/privacy-policy"
          ariaLabel="Tukar bahasa"
        />
      }
      toc={
        <LegalTOC
          items={TOC_ITEMS}
          label="Senarai Kandungan"
          mobileLabels={{
            open: 'Buka senarai kandungan',
            close: 'Tutup senarai kandungan',
          }}
        />
      }
      changelog={
        <LegalChangelog
          entries={privacyPolicyBM.changelog}
          title="Riwayat Perubahan"
          labels={{
            showAll: 'Tunjuk semua versi',
            hideOlder: 'Sembunyikan versi lama',
            versionLabel: 'Versi',
          }}
        />
      }
    />
  );
}

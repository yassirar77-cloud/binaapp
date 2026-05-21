import type { Metadata } from 'next';
import {
  LegalDocument,
  LegalLanguageToggle,
  LegalTOC,
  LegalChangelog,
  type TOCItem,
} from '@/components/legal';
import { termsBM } from '@/lib/legal/terms-content-bm';

export const metadata: Metadata = {
  title: 'Terma Perkhidmatan | BinaApp',
  description:
    'Terma Perkhidmatan BinaApp v3.0 — pelan langganan, addon, kuota, hak harta intelek, had liabiliti, dan klausa undang-undang.',
  alternates: {
    canonical: '/terma-perkhidmatan',
    languages: {
      'ms-MY': '/terma-perkhidmatan',
      en: '/terms-of-service',
    },
  },
  openGraph: {
    title: 'Terma Perkhidmatan BinaApp v3.0',
    description:
      'Terma penggunaan platform BinaApp untuk peniaga F&B di Malaysia.',
    locale: 'ms_MY',
    type: 'article',
  },
  robots: { index: true, follow: true },
};

// TOC items include the non-numbered top-of-doc anchors (executive
// summary, business model callout, intro) plus the 26 numbered sections
// plus the changelog footer anchor — in document order.
const TOC_ITEMS: TOCItem[] = [
  { id: 'ringkasan', title: termsBM.executiveSummary.title },
  { id: 'model-perniagaan', title: termsBM.businessModelCallout.title },
  { id: 'pengenalan', title: termsBM.introduction.title },
  ...termsBM.sections.map((s) => ({ id: s.id, title: s.title })),
  { id: 'riwayat-perubahan', title: 'Riwayat Perubahan' },
];

export default function TermaPerkhidmatanPage() {
  return (
    <LegalDocument
      doc={termsBM}
      docType="terms"
      language="bm"
      documentTitle="Terma Perkhidmatan BinaApp"
      languageToggle={
        <LegalLanguageToggle
          current="bm"
          bmHref="/terma-perkhidmatan"
          enHref="/terms-of-service"
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
          entries={termsBM.changelog}
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

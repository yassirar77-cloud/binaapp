import type { MetadataRoute } from 'next';

/**
 * Sitemap for binaapp.my — Next.js App Router convention.
 *
 * Currently only emits the public-facing landing page and the four
 * legal routes. The /dashboard, /edit, /delivery, /rider, and other
 * authenticated routes are deliberately excluded — they're not useful
 * to anonymous crawlers and the legal pages already disclose the
 * platform's existence to the index.
 *
 * The two language pairs (BM / EN) for each legal document are
 * cross-linked via the `alternates.languages` field — this is the
 * sitemap-level hreflang signal that complements the
 * <link rel="alternate" hreflang=…> tags emitted by each page's
 * Metadata.alternates.languages.
 *
 * Known limitation on this project (Next.js 14.1.0): the
 * `alternates.languages` field on sitemap entries is silently
 * ignored — the `<xhtml:link>` hreflang tags inside `<url>` were
 * added in Next 14.2 (release notes). The per-page
 * `<link rel="alternate" hreflang>` tags in HTML <head> are still
 * the primary SEO signal and work correctly. The field is left in
 * the sitemap config so the second signal lights up automatically
 * when the project upgrades to Next 14.2+.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://binaapp.my';
  const legalEffectiveDate = new Date('2026-05-21T00:00:00+08:00');

  const legalLanguages = (bmPath: string, enPath: string) => ({
    languages: {
      'ms-MY': `${baseUrl}${bmPath}`,
      en: `${baseUrl}${enPath}`,
    },
  });

  // `alternates` on sitemap entries is only present in the Next 14.2+ type
  // (this project targets 14.1.0 — see the note above). Build the entries with
  // a forward-compatible local type, then assert back to the framework type so
  // type-check passes on 14.1.0 and stays correct after a 14.2+ upgrade.
  type SitemapEntryWithAlternates = MetadataRoute.Sitemap[number] & {
    alternates?: { languages: Record<string, string> };
  };

  const entries: SitemapEntryWithAlternates[] = [
    {
      url: `${baseUrl}/`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${baseUrl}/polisi-privasi`,
      lastModified: legalEffectiveDate,
      changeFrequency: 'monthly',
      priority: 0.7,
      alternates: legalLanguages('/polisi-privasi', '/privacy-policy'),
    },
    {
      url: `${baseUrl}/privacy-policy`,
      lastModified: legalEffectiveDate,
      changeFrequency: 'monthly',
      priority: 0.7,
      alternates: legalLanguages('/polisi-privasi', '/privacy-policy'),
    },
    {
      url: `${baseUrl}/terma-perkhidmatan`,
      lastModified: legalEffectiveDate,
      changeFrequency: 'monthly',
      priority: 0.7,
      alternates: legalLanguages('/terma-perkhidmatan', '/terms-of-service'),
    },
    {
      url: `${baseUrl}/terms-of-service`,
      lastModified: legalEffectiveDate,
      changeFrequency: 'monthly',
      priority: 0.7,
      alternates: legalLanguages('/terma-perkhidmatan', '/terms-of-service'),
    },
  ];

  return entries as MetadataRoute.Sitemap;
}

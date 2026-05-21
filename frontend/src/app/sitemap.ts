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
 * Metadata.alternates.languages. Google and Bing both read either
 * signal, but emitting both is the recommended belt-and-suspenders
 * approach for international SEO.
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

  return [
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
}

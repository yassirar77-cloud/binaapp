import type { Metadata } from 'next'
import Link from 'next/link'
import Image from 'next/image'
import { notFound } from 'next/navigation'

import LandingFooter from '@/components/landing/LandingFooter'
import { SEO_PAGES, getSeoPage, relatedSeoPages } from '@/lib/landing/seoPages'

/**
 * Search landing pages: /bina/website-restoran, /bina/sistem-order-whatsapp, …
 *
 * Statically generated server components (no client JS of their own) so the
 * full copy is in the HTML a crawler receives. Content lives in
 * lib/landing/seoPages.ts.
 */

export const dynamicParams = false

export function generateStaticParams() {
  return SEO_PAGES.map((p) => ({ slug: p.slug }))
}

export function generateMetadata({ params }: { params: { slug: string } }): Metadata {
  const page = getSeoPage(params.slug)
  if (!page) return {}
  const path = `/bina/${page.slug}`
  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: path },
    openGraph: {
      type: 'website',
      siteName: 'BinaApp',
      locale: 'ms_MY',
      url: path,
      title: page.title,
      description: page.description,
    },
    robots: { index: true, follow: true },
  }
}

export default function SeoLandingPage({ params }: { params: { slug: string } }) {
  const page = getSeoPage(params.slug)
  if (!page) notFound()

  const faqJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: page.faqs.map((f) => ({
      '@type': 'Question',
      name: f.q,
      acceptedAnswer: { '@type': 'Answer', text: f.a },
    })),
  }

  return (
    <div className="min-h-screen bg-white">
      <script
        type="application/ld+json"
        // Content is our own static copy; "<" is escaped so it cannot close the tag.
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd).replace(/</g, '\\u003c') }}
      />

      {/* Header */}
      <header className="sticky top-0 z-30 bg-ink-900/95 backdrop-blur border-b border-white/[.06]">
        <div className="max-w-[1100px] mx-auto px-5 sm:px-8 h-16 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2.5">
            <Image src="/brand/logo-mark.svg" alt="" width={28} height={28} className="rounded-lg" />
            <span className="font-geist font-bold text-lg text-white tracking-tight">
              bina<span className="text-brand-300">app</span>
            </span>
          </Link>
          <Link
            href="/register"
            className="font-geist font-bold text-sm text-ink-950 bg-volt-400 hover:bg-volt-300 px-4 py-2.5 rounded-lg transition-colors whitespace-nowrap"
          >
            Cuba Percuma →
          </Link>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="bg-gradient-to-b from-ink-900 via-brand-900 to-brand-800 text-white px-5 sm:px-8 py-16 sm:py-24">
          <div className="max-w-[820px] mx-auto">
            <div className="font-geist-mono text-[11px] tracking-[.12em] uppercase text-volt-400 font-medium mb-5">
              {page.eyebrow}
            </div>
            <h1 className="font-geist font-extrabold text-4xl sm:text-5xl leading-[1.05] tracking-[-0.04em] mb-6 text-balance">
              {page.h1}
            </h1>
            <p className="font-geist text-lg leading-relaxed text-ink-200 mb-8 max-w-[680px]">
              {page.intro}
            </p>
            <Link
              href="/register"
              className="inline-block font-geist font-bold text-base text-ink-950 bg-volt-400 hover:bg-volt-300 px-7 py-4 rounded-xl transition-colors"
            >
              Cuba Percuma →
            </Link>
            <p className="mt-4 font-geist text-sm text-ink-200">
              Bina dan lihat website anda dulu, percuma. Bayar hanya bila anda mahu terbitkan.
            </p>
          </div>
        </section>

        {/* Features */}
        <section className="px-5 sm:px-8 py-16 sm:py-20">
          <div className="max-w-[1100px] mx-auto">
            <h2 className="font-geist font-bold text-2xl sm:text-3xl tracking-[-0.03em] text-ink-900 mb-10">
              Apa yang anda dapat
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {page.features.map((f) => (
                <div key={f.title} className="border border-ink-200 rounded-2xl p-6">
                  <h3 className="font-geist font-semibold text-lg text-ink-900 mb-2">{f.title}</h3>
                  <p className="font-geist text-base leading-relaxed text-ink-600">{f.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Steps */}
        <section className="bg-ink-050 px-5 sm:px-8 py-16 sm:py-20">
          <div className="max-w-[820px] mx-auto">
            <h2 className="font-geist font-bold text-2xl sm:text-3xl tracking-[-0.03em] text-ink-900 mb-8">
              Cara bermula
            </h2>
            <ol className="flex flex-col gap-5">
              {page.steps.map((step, i) => (
                <li key={step} className="flex gap-4">
                  <span className="flex-none w-9 h-9 rounded-full bg-brand-500 text-white font-geist font-bold text-sm flex items-center justify-center">
                    {i + 1}
                  </span>
                  <p className="font-geist text-base leading-relaxed text-ink-700 pt-1.5">{step}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* FAQ */}
        <section className="px-5 sm:px-8 py-16 sm:py-20">
          <div className="max-w-[820px] mx-auto">
            <h2 className="font-geist font-bold text-2xl sm:text-3xl tracking-[-0.03em] text-ink-900 mb-8">
              Soalan lazim
            </h2>
            <div className="flex flex-col gap-7">
              {page.faqs.map((f) => (
                <div key={f.q}>
                  <h3 className="font-geist font-semibold text-lg text-ink-900 mb-2">{f.q}</h3>
                  <p className="font-geist text-base leading-relaxed text-ink-600">{f.a}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Closing CTA */}
        <section className="bg-ink-900 text-white px-5 sm:px-8 py-16 text-center">
          <div className="max-w-[640px] mx-auto">
            <h2 className="font-geist font-bold text-2xl sm:text-3xl tracking-[-0.03em] mb-4 text-balance">
              Lihat website kedai anda dalam 60 saat
            </h2>
            <p className="font-geist text-base text-ink-300 mb-7">
              Tiada kad kredit diperlukan untuk mencuba. Tiada komisen selepas itu.
            </p>
            <Link
              href="/register"
              className="inline-block font-geist font-bold text-base text-ink-950 bg-volt-400 hover:bg-volt-300 px-7 py-4 rounded-xl transition-colors"
            >
              Cuba Percuma →
            </Link>
          </div>
        </section>

        {/* Related pages */}
        <nav aria-label="Halaman berkaitan" className="px-5 sm:px-8 py-12">
          <div className="max-w-[1100px] mx-auto">
            <h2 className="font-geist-mono text-[11px] tracking-[.12em] uppercase text-ink-500 mb-4">
              Lihat juga
            </h2>
            <ul className="flex flex-wrap gap-x-6 gap-y-3">
              {relatedSeoPages(page.slug, SEO_PAGES.length).map((p) => (
                <li key={p.slug}>
                  <Link
                    href={`/bina/${p.slug}`}
                    className="font-geist text-base text-brand-600 hover:text-brand-800 underline underline-offset-4"
                  >
                    {p.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </nav>
      </main>

      <LandingFooter />
    </div>
  )
}

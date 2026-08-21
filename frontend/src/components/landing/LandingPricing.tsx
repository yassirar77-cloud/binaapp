'use client'

import Link from 'next/link'

interface LandingPricingProps {
  onSelectPlan: (tier: 'starter' | 'pro') => void
}

// Two-tier lineup: Permulaan (online presence) and Bisnes (delivery
// operations). The retired Asas RM29 tier is grandfathered for existing
// subscribers but no longer sold — the backend rejects new basic purchases.
const tiers = [
  {
    name: 'Permulaan',
    price: 'RM 5',
    tier: 'starter' as const,
    tagline: 'Untuk mula berniaga online',
    features: [
      '1 website',
      'Subdomain percuma',
      'Imej AI percuma',
      'WhatsApp + troli',
      'Sokongan melalui email',
    ],
    cta: 'Mula sekarang',
    variant: 'default',
  },
  {
    name: 'Bisnes',
    price: 'RM 49',
    tier: 'pro' as const,
    tagline: 'Sistem penghantaran penuh — tanpa komisen',
    features: [
      'Semua dalam Permulaan',
      'Website & zon tanpa had',
      'Rider sendiri + GPS tracking (10)',
      'Dashboard order & chat pelanggan',
      'Analitik penuh',
    ],
    cta: 'Pilih Bisnes',
    variant: 'dark',
  },
]

export default function LandingPricing({ onSelectPlan }: LandingPricingProps) {
  return (
    <section id="harga" className="bg-oat-50 py-20 lg:py-28 px-8">
      <div className="max-w-[1200px] mx-auto">

        {/* Header */}
        <div className="text-center mb-14">
          <div className="font-geist text-xs tracking-[.12em] uppercase text-clay-600 font-semibold mb-3">
            — Harga
          </div>
          <h2 className="font-display font-medium text-3xl sm:text-4xl lg:text-[52px] leading-[1.08] tracking-[-0.02em] text-carbon-900">
            Lima ringgit. Bukan 30 peratus.
          </h2>
          <p className="font-geist text-lg text-carbon-400 mt-3.5">
            Satu harga tetap sebulan. Tiada komisen. Tiada caj tersembunyi.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-[820px] mx-auto">
          {tiers.map((t) => {
            const isDark = t.variant === 'dark'

            return (
              <div
                key={t.name}
                className={`relative rounded-3xl p-8 ${
                  isDark
                    ? 'bg-carbon-900 border border-carbon-700 shadow-lift-warm'
                    : 'bg-white border border-oat-300 shadow-card-warm'
                }`}
              >
                {/* Business badge */}
                {isDark && (
                  <span className="absolute -top-3 left-6 bg-clay-500 text-white font-geist font-bold text-[11px] px-3 py-1 rounded-full tracking-[.08em] shadow-card-warm">
                    UNTUK BISNES
                  </span>
                )}

                {/* Tier name */}
                <div className={`font-geist text-[11px] tracking-[.12em] uppercase font-semibold mb-4 ${
                  isDark ? 'text-clay-400' : 'text-carbon-300'
                }`}>
                  {t.name}
                </div>

                {/* Price */}
                <div className={`font-display font-medium text-5xl lg:text-6xl tracking-[-0.02em] leading-none mb-1.5 ${
                  isDark ? 'text-oat-50' : 'text-carbon-900'
                }`}>
                  {t.price}
                  <span className={`font-geist text-base font-medium tracking-tight ${
                    isDark ? 'text-carbon-200' : 'text-carbon-400'
                  }`}>
                    /bln
                  </span>
                </div>

                {/* Tagline */}
                <p className={`font-geist text-sm mt-2 ${isDark ? 'text-carbon-200' : 'text-carbon-400'}`}>
                  {t.tagline}
                </p>

                {/* Feature list */}
                <ul className="flex flex-col gap-2.5 my-7">
                  {t.features.map((f) => (
                    <li key={f} className={`font-geist text-sm flex items-center gap-2.5 ${
                      isDark ? 'text-oat-50' : 'text-carbon-900'
                    }`}>
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={isDark ? '#DE9877' : '#C15F3C'}
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="flex-shrink-0"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      {f}
                    </li>
                  ))}
                </ul>

                {/* CTA button */}
                {t.tier === 'starter' ? (
                  <Link
                    href="/register"
                    className="block w-full text-center font-geist font-semibold text-[15px] py-3.5 rounded-xl tracking-tight transition-colors bg-carbon-900 text-oat-50 hover:bg-carbon-700"
                  >
                    Mula Percuma →
                  </Link>
                ) : (
                  <button
                    onClick={() => onSelectPlan(t.tier)}
                    className="w-full font-geist font-semibold text-[15px] py-3.5 rounded-xl tracking-tight transition-colors bg-clay-500 text-white shadow-glow-clay hover:bg-clay-600"
                  >
                    {t.cta} →
                  </button>
                )}
              </div>
            )
          })}
        </div>

        {/* Commission comparison note */}
        <p className="text-center font-geist text-sm text-carbon-400 mt-8 max-w-[560px] mx-auto">
          Platform penghantaran ambil 25–30% komisen setiap order. Dengan pelan
          Bisnes, RM49 sebulan — rider sendiri, GPS tracking, tiada komisen.
        </p>
      </div>
    </section>
  )
}

'use client'

import Link from 'next/link'

interface LandingPricingProps {
  onSelectPlan: (tier: 'starter' | 'basic' | 'pro') => void
}

const tiers = [
  {
    name: 'Permulaan',
    price: 'RM 5',
    tier: 'starter' as const,
    features: [
      '1 website',
      'Subdomain percuma',
      'Penjanaan AI (1/bln)',
      'WhatsApp + troli',
      'Sokongan melalui email',
    ],
    cta: 'Mula sekarang',
    variant: 'default',
  },
  {
    name: 'Asas',
    price: 'RM 29',
    tier: 'basic' as const,
    features: [
      '5 website',
      'Subdomain tersendiri',
      'Keutamaan AI (10/bln)',
      'Analitik penuh',
      'Sokongan keutamaan',
    ],
    cta: 'Pilih Asas',
    variant: 'highlight',
  },
  {
    name: 'Pro',
    price: 'RM 49',
    tier: 'pro' as const,
    features: [
      'Website tanpa had',
      'AI tanpa had',
      'Zon tanpa had',
      'GPS penghantar (10)',
      'AI tahap lanjut',
    ],
    cta: 'Pilih Pro',
    variant: 'dark',
  },
]

export default function LandingPricing({ onSelectPlan }: LandingPricingProps) {
  return (
    <section id="harga" className="bg-white py-20 lg:py-28 px-8">
      <div className="max-w-[1200px] mx-auto">

        {/* Header */}
        <div className="text-center mb-14">
          <div className="font-geist-mono text-xs tracking-[.12em] uppercase text-brand-500 font-semibold mb-3">
            — Harga
          </div>
          <h2 className="font-geist font-bold text-3xl sm:text-4xl lg:text-[56px] leading-[1.02] tracking-[-0.045em] text-ink-900">
            Lima ringgit. Bukan 30 peratus.
          </h2>
          <p className="font-geist text-lg text-ink-500 mt-3.5">
            Satu harga tetap sebulan. Tiada komisen. Tiada caj tersembunyi.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-[1100px] mx-auto">
          {tiers.map((t) => {
            const isDark = t.variant === 'dark'
            const isHl = t.variant === 'highlight'

            return (
              <div
                key={t.name}
                className={`relative rounded-3xl p-8 ${
                  isDark
                    ? 'bg-ink-900 border border-white/[.08]'
                    : isHl
                      ? 'bg-white border-2 border-brand-500 shadow-[0_24px_60px_rgba(79,61,255,.2)]'
                      : 'bg-white border border-ink-200'
                }`}
              >
                {/* Popular badge */}
                {isHl && (
                  <span className="absolute -top-3 left-6 bg-volt-400 text-ink-900 font-geist-mono font-bold text-[11px] px-3 py-1 rounded-full tracking-[.08em] shadow-[0_4px_12px_rgba(199,255,61,.4)]">
                    PALING POPULAR
                  </span>
                )}

                {/* Tier name */}
                <div className={`font-geist-mono text-[11px] tracking-[.12em] uppercase font-semibold mb-4 ${
                  isDark ? 'text-volt-400' : isHl ? 'text-brand-500' : 'text-ink-400'
                }`}>
                  {t.name}
                </div>

                {/* Price */}
                <div className={`font-geist font-extrabold text-5xl lg:text-6xl tracking-[-0.045em] leading-none mb-1.5 ${
                  isDark ? 'text-white' : 'text-ink-900'
                }`}>
                  {t.price}
                  <span className={`text-base font-medium tracking-tight ${
                    isDark ? 'text-ink-300' : 'text-ink-500'
                  }`}>
                    /bln
                  </span>
                </div>

                {/* Feature list */}
                <ul className="flex flex-col gap-2.5 my-7">
                  {t.features.map((f) => (
                    <li key={f} className={`font-geist text-sm flex items-center gap-2.5 ${
                      isDark ? 'text-white' : 'text-ink-900'
                    }`}>
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={isHl ? '#4F3DFF' : isDark ? '#C7FF3D' : '#22C08F'}
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
                    className="block w-full text-center font-geist font-bold text-[15px] py-3.5 rounded-xl tracking-tight transition-colors bg-ink-900 text-white hover:bg-ink-800"
                  >
                    Mula Percuma →
                  </Link>
                ) : (
                  <button
                    onClick={() => onSelectPlan(t.tier)}
                    className={`w-full font-geist font-bold text-[15px] py-3.5 rounded-xl tracking-tight transition-colors ${
                      isHl
                        ? 'bg-brand-500 text-white shadow-[0_0_0_1px_theme(colors.brand.500),0_10px_24px_rgba(79,61,255,.35)] hover:bg-brand-400'
                        : 'bg-volt-400 text-ink-900 shadow-[0_0_0_1px_theme(colors.volt.500),0_10px_24px_rgba(199,255,61,.35)] hover:bg-volt-300'
                    }`}
                  >
                    {t.cta} →
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

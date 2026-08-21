import Link from 'next/link'
import Image from 'next/image'

export default function LandingHero() {
  return (
    <section className="relative overflow-hidden bg-oat-50 text-carbon-900 pt-20 pb-14 px-8">

      {/* Soft terracotta wash — top right */}
      <div className="absolute -top-[140px] -right-[8%] w-[520px] h-[520px] rounded-full bg-[radial-gradient(circle,rgba(217,119,87,.12),transparent_65%)] pointer-events-none" />

      {/* Warm cream wash — bottom left */}
      <div className="absolute -bottom-[160px] -left-[10%] w-[480px] h-[480px] rounded-full bg-[radial-gradient(circle,rgba(222,219,207,.55),transparent_65%)] pointer-events-none" />

      {/* Content grid */}
      <div className="relative max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-12 items-center">

        {/* Left column — copy */}
        <div>
          {/* Eyebrow pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 border border-clay-500/30 bg-clay-50 rounded-full font-geist text-[11px] tracking-[.12em] uppercase text-clay-600 font-semibold mb-7">
            <span className="w-1.5 h-1.5 rounded-full bg-clay-500" />
            Dibina untuk restoran Malaysia
          </div>

          {/* Headline — serif display, Claude-style */}
          <h1 className="font-display font-medium text-5xl sm:text-6xl lg:text-[68px] leading-[1.05] tracking-[-0.02em] mb-8">
            Borak dengan AI.<br />
            Website restoran siap<br />
            <span className="text-clay-500 italic">
              dalam 60 saat.
            </span>
          </h1>

          {/* Subtext */}
          <p className="font-geist text-lg leading-relaxed text-carbon-400 max-w-[520px] mb-8">
            Ceritakan kedai anda dalam Bahasa Melayu. AI akan bina website penuh
            dengan menu, pesanan WhatsApp, dan jejakan penghantar. Berhenti bayar
            30% komisen platform penghantaran — miliki pelanggan anda sendiri.
          </p>

          {/* CTA — single button, links to /register */}
          <Link
            href="/register"
            className="inline-block font-geist font-semibold text-base text-white bg-clay-500 px-7 py-4 rounded-xl shadow-lift-warm hover:bg-clay-600 transition-colors tracking-tight"
          >
            Mula Percuma — RM 5/bln →
          </Link>

          {/* Trust line */}
          <div className="flex flex-wrap gap-x-6 gap-y-2 mt-7 font-geist-mono text-[11px] text-carbon-300 tracking-[.06em]">
            <span>✓ AI BINA DALAM BM / MANGLISH</span>
            <span>✓ PESANAN WHATSAPP AUTO</span>
            <span>✓ TOYYIBPAY SEDIA</span>
          </div>
        </div>

        {/* Right column — hero image + floating badges */}
        <div className="relative">
          <Image
            src="/brand/hero-mamak.svg"
            alt="Ilustrasi kedai mamak dengan sistem pesanan BinaApp"
            width={580}
            height={420}
            priority
            className="w-full h-auto rounded-2xl border border-oat-300 shadow-lift-warm"
          />

          {/* Floating badge — top left: daily orders */}
          <div className="absolute -top-4 -left-4 lg:-top-5 lg:-left-5 bg-white border border-oat-300 rounded-xl px-3.5 py-2.5 shadow-card-warm">
            <div className="font-geist-mono text-[10px] text-carbon-400 tracking-[.1em] font-semibold whitespace-nowrap">
              PESANAN HARI INI
            </div>
            <div className="font-geist font-extrabold text-2xl text-carbon-900 tracking-tight tabular-nums">
              RM 1,284
            </div>
          </div>

          {/* Floating badge — bottom right: zero commission */}
          <div className="absolute -bottom-4 -right-3 lg:-bottom-5 lg:-right-3 bg-clay-500 rounded-xl px-4 py-2.5 shadow-lift-warm">
            <div className="font-geist-mono text-[10px] text-white/80 tracking-[.1em] font-bold whitespace-nowrap">
              KOMISEN DIBAYAR
            </div>
            <div className="font-geist font-extrabold text-2xl text-white tracking-tight tabular-nums">
              RM 0.00
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

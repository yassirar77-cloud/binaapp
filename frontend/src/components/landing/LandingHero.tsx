import Link from 'next/link'
import Image from 'next/image'

export default function LandingHero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-ink-900 via-brand-900 to-brand-800 text-white pt-20 pb-10 px-8">

      {/* Background dot grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,.05) 1px, transparent 0)',
          backgroundSize: '36px 36px',
          maskImage: 'radial-gradient(ellipse at top, black 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse at top, black 30%, transparent 75%)',
        }}
      />

      {/* Lime glow — left */}
      <div className="absolute top-[120px] -left-[10%] w-[400px] h-[400px] rounded-full bg-[radial-gradient(circle,rgba(199,255,61,.15),transparent_65%)] pointer-events-none" />

      {/* Indigo glow — right */}
      <div className="absolute -bottom-[100px] -right-[5%] w-[500px] h-[500px] rounded-full bg-[radial-gradient(circle,rgba(79,61,255,.35),transparent_65%)] pointer-events-none" />

      {/* Content grid */}
      <div className="relative max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-12 items-center">

        {/* Left column — copy */}
        <div>
          {/* Eyebrow pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 border border-volt-400/30 bg-volt-400/[.08] rounded-full font-geist-mono text-[11px] tracking-[.12em] uppercase text-volt-400 font-medium mb-7">
            <span className="w-1.5 h-1.5 rounded-full bg-volt-400 shadow-[0_0_12px_theme(colors.volt.400)]" />
            Dibina untuk restoran Malaysia
          </div>

          {/* Headline */}
          <h1 className="font-geist font-extrabold text-5xl sm:text-6xl lg:text-7xl leading-[1.02] tracking-[-0.045em] mb-8">
            Borak dengan AI.<br />
            Website restoran siap<br />
            <span className="text-volt-400 drop-shadow-[0_0_40px_rgba(199,255,61,.4)]">
              dalam 60 saat.
            </span>
          </h1>

          {/* Subtext */}
          <p className="font-geist text-lg leading-relaxed text-ink-300 max-w-[520px] mb-8">
            Ceritakan kedai anda dalam Bahasa Melayu. AI akan bina website penuh
            dengan menu, pesanan WhatsApp, dan jejakan penghantar. Berhenti bayar
            30% komisen Foodpanda — miliki pelanggan anda sendiri.
          </p>

          {/* CTA — single button, links to /register */}
          <Link
            href="/register"
            className="inline-block font-geist font-bold text-base text-ink-950 bg-volt-400 px-7 py-4 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_0_30px_rgba(199,255,61,.4),0_20px_48px_rgba(199,255,61,.3)] hover:bg-volt-300 transition-colors tracking-tight"
          >
            Mula Percuma — RM 5/bln →
          </Link>

          {/* Trust line */}
          <div className="flex flex-wrap gap-x-6 gap-y-2 mt-7 font-geist-mono text-[11px] text-ink-400 tracking-[.06em]">
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
            className="w-full h-auto rounded-2xl shadow-[0_30px_80px_rgba(79,61,255,.4),0_0_0_1px_rgba(199,255,61,.15)]"
          />

          {/* Floating badge — top left: daily orders */}
          <div className="absolute -top-4 -left-4 lg:-top-5 lg:-left-5 bg-ink-900 border border-volt-400/40 rounded-xl px-3.5 py-2.5 shadow-[0_20px_40px_rgba(0,0,0,.4)]">
            <div className="font-geist-mono text-[10px] text-volt-400 tracking-[.1em] font-semibold whitespace-nowrap">
              PESANAN HARI INI
            </div>
            <div className="font-geist font-extrabold text-2xl text-white tracking-tight tabular-nums">
              RM 1,284
            </div>
          </div>

          {/* Floating badge — bottom right: zero commission */}
          <div className="absolute -bottom-4 -right-3 lg:-bottom-5 lg:-right-3 bg-volt-400 rounded-xl px-4 py-2.5 shadow-[0_20px_40px_rgba(199,255,61,.35)]">
            <div className="font-geist-mono text-[10px] text-ink-900 tracking-[.1em] font-bold whitespace-nowrap">
              KOMISEN DIBAYAR
            </div>
            <div className="font-geist font-extrabold text-2xl text-ink-900 tracking-tight tabular-nums">
              RM 0.00
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

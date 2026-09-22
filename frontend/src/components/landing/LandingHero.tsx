import Link from 'next/link'

import HeroFilm from './HeroFilm'

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

      {/*
        Three children, placed rather than flowed. Stacked on a phone they come
        out in source order — copy, film, trust line — which puts the film
        directly under the button. On a wide screen the explicit rows and
        columns put the copy above the trust line on the left and give the film
        the whole right-hand column, without the trust line having to exist
        twice in the markup to be in the right place in both layouts.
      */}
      <div className="relative max-w-[1200px] mx-auto grid grid-cols-1 lg:grid-cols-[1.08fr_1fr] lg:grid-rows-[auto_auto] gap-y-10 gap-x-12 lg:gap-y-7 items-start">

        {/* Copy */}
        <div className="lg:col-start-1 lg:row-start-1">
          {/* Eyebrow pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 border border-volt-400/30 bg-volt-400/[.08] rounded-full font-geist-mono text-[11px] tracking-[.12em] uppercase text-volt-400 font-medium mb-7">
            <span className="w-1.5 h-1.5 rounded-full bg-volt-400 shadow-[0_0_12px_theme(colors.volt.400)]" />
            Dibina untuk restoran Malaysia
          </div>

          {/*
            The size steps back down at lg and up again at xl because that is
            where the column changes, not the viewport. Below lg the copy has
            the page to itself; from lg it has half of it, and half of a
            1200px page is 456px at 1024 and 576px from 1264 up. In Geist
            ExtraBold, "Website restoran siap" measures 595px at 72px, 485 at
            60 and 374 at 48 — so 72 broke mid-phrase at every desktop width,
            and these two fit at theirs with room to spare. The margin is
            deliberate: Geist is loaded from Google Fonts, and until it
            arrives — or for good, if it cannot be reached — the line is set
            in a fallback that measures wider.
          */}
          <h1 className="font-geist font-extrabold text-5xl sm:text-6xl lg:text-5xl xl:text-6xl leading-[1.02] tracking-[-0.045em] mb-8">
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
            30% komisen platform penghantaran — miliki pelanggan anda sendiri.
          </p>

          {/* CTA — single button, links to /register */}
          <Link
            href="/register"
            className="inline-block font-geist font-bold text-base text-ink-950 bg-volt-400 px-7 py-4 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_0_30px_rgba(199,255,61,.4),0_20px_48px_rgba(199,255,61,.3)] hover:bg-volt-300 transition-colors tracking-tight"
          >
            Mula Percuma — RM 5/bln →
          </Link>
        </div>

        {/* The film */}
        <div className="lg:col-start-2 lg:row-start-1 lg:row-span-2 lg:self-center">
          <HeroFilm />
        </div>

        {/* Trust line */}
        <div className="flex flex-wrap gap-x-6 gap-y-2 font-geist-mono text-[11px] text-ink-400 tracking-[.06em] lg:col-start-1 lg:row-start-2">
          <span>✓ AI BINA DALAM BM / MANGLISH</span>
          <span>✓ PESANAN WHATSAPP AUTO</span>
          <span>✓ TOYYIBPAY SEDIA</span>
        </div>
      </div>
    </section>
  )
}

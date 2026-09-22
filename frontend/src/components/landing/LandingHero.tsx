import Link from 'next/link'

import HeroFilm from './HeroFilm'

/**
 * The hero is the film, full bleed, with the copy over it.
 *
 * It fills what is left of the viewport under the sticky nav — 65px of it on a
 * phone, 69px from lg — rather than 100svh, which would have pushed the button
 * off the first screen by exactly the height of the bar above it.
 *
 * The gradient on the section is not decoration: it is what the hero looks like
 * if the film cannot be decoded or has not been generated yet, and HeroFilm
 * removes itself in that case rather than leaving a black hole.
 */
export default function LandingHero() {
  return (
    <section className="relative isolate flex min-h-[calc(100svh-65px)] items-center overflow-hidden bg-gradient-to-b from-ink-900 via-brand-900 to-brand-800 px-6 py-16 text-white sm:px-8 lg:min-h-[calc(100svh-69px)]">

      <HeroFilm />

      {/*
        Two scrims over the film. The flat one holds the whole frame down so
        the picture never competes with the type; the gradient pours the dark
        in from the side the copy is on — up from the bottom on a phone, in
        from the left once there is a left. Without the second one the headline
        sits over whichever part of the film happens to be playing, and two of
        the four shots are a phone screen full of small text.

        The phone is held down harder than the desktop is, and its gradient
        never reaches transparent. On a wide screen the copy has a side to
        itself and the film has the other; on a phone the copy runs down the
        whole frame, and the shot of her finished site put her headline
        directly behind ours until the top of the scrim came up to 55%.
      */}
      <div className="absolute inset-0 z-10 bg-ink-950/65 lg:bg-ink-950/50" />
      <div className="absolute inset-0 z-10 bg-gradient-to-t from-ink-950 via-ink-950/80 to-ink-950/55 lg:bg-gradient-to-r lg:from-ink-950 lg:via-ink-950/80 lg:to-transparent" />

      {/* Copy */}
      <div className="relative z-20 mx-auto w-full max-w-[1200px]">
        <div className="max-w-[640px]">

          {/* Eyebrow pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 border border-volt-400/30 bg-volt-400/[.08] rounded-full font-geist-mono text-[11px] tracking-[.12em] uppercase text-volt-400 font-medium mb-7 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-volt-400 shadow-[0_0_12px_theme(colors.volt.400)]" />
            Dibina untuk restoran Malaysia
          </div>

          {/*
            60px from sm up, and no step at lg any more: the copy now has a
            640px column of its own instead of half a 1200px grid, and
            "Website restoran siap" measures 485px at 60 in Geist ExtraBold,
            566 in the wider fallback that renders until Geist arrives. Both
            fit, so the line stays whole at every width above sm.
          */}
          <h1 className="font-geist font-extrabold text-5xl sm:text-6xl leading-[1.02] tracking-[-0.045em] mb-8 drop-shadow-[0_2px_24px_rgba(0,0,0,.55)]">
            Borak dengan AI.<br />
            Website restoran siap<br />
            <span className="text-volt-400 drop-shadow-[0_0_40px_rgba(199,255,61,.4)]">
              dalam 60 saat.
            </span>
          </h1>

          {/* Subtext */}
          <p className="font-geist text-lg leading-relaxed text-ink-200 max-w-[520px] mb-8 drop-shadow-[0_1px_12px_rgba(0,0,0,.6)]">
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

          {/* Trust line */}
          <div className="flex flex-wrap gap-x-6 gap-y-2 mt-7 font-geist-mono text-[11px] text-ink-300 tracking-[.06em]">
            <span>✓ AI BINA DALAM BM / MANGLISH</span>
            <span>✓ PESANAN WHATSAPP AUTO</span>
            <span>✓ TOYYIBPAY SEDIA</span>
          </div>
        </div>
      </div>
    </section>
  )
}

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
        The scrim covers the copy, not the picture.

        It used to be a flat 50% over everything plus a gradient that reached
        full ink-950 at the left, and the two multiplied: the clear side of the
        frame showed half the film and the copy side showed none of it. The
        film is a dark restaurant to begin with — its own mean luma runs 26 to
        53 of 255 across the four shots — so halving that again left a black
        rectangle where the picture was meant to be.

        Now the flat layer is gone from desktop entirely and the gradient is
        shaped: it starts at 92%, is down to 45% by 38% across, and is
        transparent from 68% on, so the right two fifths of the frame are the
        film at its own colour. A phone keeps a light flat layer and a slower
        fade, because there the copy runs down the whole frame rather than
        sitting beside the picture.

        What the type lost in blanket dimming it gets back in its own shadow,
        which darkens the pixels behind the letters instead of the whole shot.
      */}
      <div className="absolute inset-0 z-10 bg-ink-950/30 lg:bg-transparent" />
      <div className="absolute inset-0 z-10 bg-gradient-to-t from-ink-950/95 via-ink-950/60 via-45% to-ink-950/15 lg:bg-gradient-to-r lg:from-ink-950/92 lg:via-ink-950/45 lg:via-38% lg:to-transparent lg:to-68%" />

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
          <h1 className="font-geist font-extrabold text-5xl sm:text-6xl leading-[1.02] tracking-[-0.045em] mb-8 [text-shadow:0_2px_18px_rgba(0,0,0,.85),0_1px_4px_rgba(0,0,0,.7)]">
            Borak dengan AI.<br />
            Website restoran siap<br />
            <span className="text-volt-400 drop-shadow-[0_0_40px_rgba(199,255,61,.4)]">
              dalam 60 saat.
            </span>
          </h1>

          {/* Subtext */}
          <p className="font-geist text-lg leading-relaxed text-ink-200 max-w-[520px] mb-8 [text-shadow:0_1px_10px_rgba(0,0,0,.9),0_1px_3px_rgba(0,0,0,.8)]">
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
          <div className="flex flex-wrap gap-x-6 gap-y-2 mt-7 font-geist-mono text-[11px] text-ink-200 tracking-[.06em] [text-shadow:0_1px_6px_rgba(0,0,0,.9)]">
            <span>✓ AI BINA DALAM BM / MANGLISH</span>
            <span>✓ PESANAN WHATSAPP AUTO</span>
            <span>✓ TOYYIBPAY SEDIA</span>
          </div>
        </div>
      </div>
    </section>
  )
}

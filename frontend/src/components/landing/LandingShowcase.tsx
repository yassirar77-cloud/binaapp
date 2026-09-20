'use client'

/**
 * The moving showcase wall — real merchant sites, running.
 *
 * Columns of cards drift in alternating directions, each card a short loop of
 * one BinaApp site in use: the page scrolling, an order landing in WhatsApp,
 * the rider map moving. Card heights are deliberately uneven so the grid
 * staggers rather than marching in rows.
 *
 * Three things keep it cheap:
 *  - videos only play while the section is on screen and the tab is visible;
 *    everything pauses otherwise,
 *  - `prefers-reduced-motion` stops the drift and the playback, leaving the
 *    posters,
 *  - a clip with no `src` (or one whose file 404s) draws a gradient card
 *    instead, so the wall never shows a broken frame.
 *
 * The clip list lives in `@/lib/landing/showcaseClips`.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import {
  SHOWCASE_CLIPS,
  dealClipsIntoColumns,
  type ShowcaseClip,
} from '@/lib/landing/showcaseClips'

const COLUMN_COUNT = 5

/** Seconds for one full pass, per column. Uneven on purpose — matching
 *  durations make the columns look locked together. */
const COLUMN_DURATIONS = [58, 46, 70, 52, 64]

/** Narrow screens get two columns; the grid below drops the rest at the same
 *  breakpoints so the cards stay their size instead of stretching. */
const COLUMN_VISIBILITY = ['flex', 'flex', 'hidden md:flex', 'hidden lg:flex', 'hidden xl:flex']

const RATIO_CLASS: Record<ShowcaseClip['ratio'], string> = {
  tall: 'aspect-[9/16]',
  portrait: 'aspect-[3/4]',
  square: 'aspect-square',
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const sync = () => setReduced(query.matches)
    sync()
    query.addEventListener('change', sync)
    return () => query.removeEventListener('change', sync)
  }, [])

  return reduced
}

type ClipCardProps = {
  clip: ShowcaseClip
  registerVideo: (video: HTMLVideoElement | null) => void
}

function ClipCard({ clip, registerVideo }: ClipCardProps) {
  const [failed, setFailed] = useState(false)
  const showVideo = Boolean(clip.src) && !failed

  return (
    <div className="pb-3 sm:pb-4">
      <div
        className={`relative w-full overflow-hidden rounded-2xl ring-1 ring-white/10 shadow-[0_18px_44px_rgba(5,5,12,.5)] ${RATIO_CLASS[clip.ratio]}`}
        style={{ background: `linear-gradient(145deg, ${clip.from}, ${clip.to})` }}
      >
        {showVideo ? (
          <video
            ref={registerVideo}
            src={clip.src}
            poster={clip.poster}
            muted
            loop
            playsInline
            preload="none"
            disablePictureInPicture
            onError={() => setFailed(true)}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          /* No file yet — the card draws itself. */
          <>
            <div
              className="absolute inset-0 opacity-70"
              style={{
                backgroundImage:
                  'radial-gradient(circle at 30% 20%, rgba(255,255,255,.28), transparent 55%)',
              }}
            />
            <div
              className="absolute inset-0 opacity-30"
              style={{
                backgroundImage:
                  'radial-gradient(circle at 1px 1px, rgba(255,255,255,.35) 1px, transparent 0)',
                backgroundSize: '14px 14px',
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-5xl drop-shadow-[0_6px_18px_rgba(5,5,12,.55)] sm:text-6xl">
                {clip.mark}
              </span>
            </div>
          </>
        )}

        {/* Caption — the same on a video card and a drawn one. */}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink-950/92 via-ink-950/55 to-transparent px-3.5 pb-3 pt-10 sm:px-4 sm:pb-3.5">
          <div className="mb-0.5 font-geist-mono text-[9px] font-semibold uppercase tracking-[.14em] text-volt-400">
            {clip.kind}
          </div>
          <div className="font-geist text-sm font-bold uppercase leading-tight tracking-tight text-white sm:text-base">
            {clip.label}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function LandingShowcase() {
  const wallRef = useRef<HTMLDivElement>(null)
  const videosRef = useRef<Set<HTMLVideoElement>>(new Set())
  const [onScreen, setOnScreen] = useState(false)
  const [tabVisible, setTabVisible] = useState(true)
  const reducedMotion = usePrefersReducedMotion()

  const playing = onScreen && tabVisible && !reducedMotion

  const columns = useMemo(() => dealClipsIntoColumns(SHOWCASE_CLIPS, COLUMN_COUNT), [])

  // Only run while the wall is in view — a dozen videos playing under the
  // pricing table is pure battery burn.
  useEffect(() => {
    const wall = wallRef.current
    if (!wall) return

    const observer = new IntersectionObserver(
      ([entry]) => setOnScreen(entry.isIntersecting),
      { rootMargin: '200px' }
    )
    observer.observe(wall)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const sync = () => setTabVisible(document.visibilityState === 'visible')
    sync()
    document.addEventListener('visibilitychange', sync)
    return () => document.removeEventListener('visibilitychange', sync)
  }, [])

  useEffect(() => {
    videosRef.current.forEach((video) => {
      if (playing) {
        // Autoplay can still be refused (data saver, low power mode); the
        // poster or the gradient underneath stays put when it is.
        void video.play().catch(() => {})
      } else {
        video.pause()
      }
    })
  }, [playing])

  const registerVideo = (video: HTMLVideoElement | null) => {
    if (!video) return
    videosRef.current.add(video)
    if (playing) void video.play().catch(() => {})
  }

  return (
    <section id="showcase" className="relative overflow-hidden bg-ink-950 py-20 lg:py-28">

      {/* Indigo glow behind the wall */}
      <div className="pointer-events-none absolute left-1/2 top-0 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(79,61,255,.25),transparent_65%)]" />

      {/* Heading */}
      <div className="relative mx-auto mb-12 max-w-[760px] px-4 text-center sm:px-8 lg:mb-16">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-volt-400/30 bg-volt-400/[.08] px-3.5 py-1.5 font-geist-mono text-[11px] font-medium uppercase tracking-[.12em] text-volt-400">
          <span className="h-1.5 w-1.5 rounded-full bg-volt-400 shadow-[0_0_12px_theme(colors.volt.400)]" />
          Website sebenar, bukan mockup
        </div>
        <h2 className="mb-5 font-geist text-3xl font-extrabold leading-[1.08] tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl">
          Tengok sendiri website<br />
          <span className="text-volt-400">yang AI dah bina.</span>
        </h2>
        <p className="font-geist text-base leading-relaxed text-ink-300 sm:text-lg">
          Setiap satu dibina dari satu perbualan — menu, gambar, pesanan
          WhatsApp dan jejakan penghantar, siap terus.
        </p>
      </div>

      {/* The wall */}
      <div ref={wallRef} aria-hidden="true" className="pointer-events-none relative h-[560px] sm:h-[640px] lg:h-[720px]">
        <div className="grid h-full grid-cols-2 gap-3 px-3 sm:gap-4 sm:px-4 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {columns.map((column, index) => (
            <div key={index} className={`${COLUMN_VISIBILITY[index]} flex-col overflow-hidden`}>
              <div
                className="animate-showcase-marquee will-change-transform"
                style={{
                  animationDuration: `${COLUMN_DURATIONS[index]}s`,
                  animationDirection: index % 2 === 1 ? 'reverse' : 'normal',
                  animationPlayState: playing ? 'running' : 'paused',
                }}
              >
                {/* Doubled so the -50% translate loops seamlessly. The bottom
                    padding lives on each card, not as a grid gap, so the two
                    halves are exactly the same height. */}
                {[...column, ...column].map((clip, position) => (
                  <ClipCard
                    key={`${clip.id}-${position}`}
                    clip={clip}
                    registerVideo={registerVideo}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Fade the columns into the section top and bottom so cards are never
            seen entering or leaving. */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-ink-950 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-ink-950 to-transparent" />
      </div>

      {/* CTA under the wall */}
      <div className="relative mt-12 px-4 text-center lg:mt-14">
        <Link
          href="/register"
          className="inline-block rounded-xl bg-volt-400 px-7 py-4 font-geist text-base font-bold tracking-tight text-ink-950 shadow-[0_0_0_1px_theme(colors.volt.500),0_0_30px_rgba(199,255,61,.4),0_20px_48px_rgba(199,255,61,.3)] transition-colors hover:bg-volt-300"
        >
          Bina website saya →
        </Link>
      </div>
    </section>
  )
}

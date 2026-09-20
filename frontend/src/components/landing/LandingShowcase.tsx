'use client'

/**
 * The showcase wall — merchant sites, each card playing that site's own hero
 * video. A plain masonry grid the visitor scrolls past; nothing moves on its
 * own. Card heights are uneven so the grid staggers instead of marching in
 * rows.
 *
 * Two things keep a wall of videos cheap. `preload="none"` means a card costs
 * nothing until it is reached, and one IntersectionObserver plays each video
 * as it enters the viewport and pauses it as it leaves — so at most a screen's
 * worth is ever running. `prefers-reduced-motion` holds every card on its
 * poster instead.
 *
 * A clip whose file has not been uploaded yet (or 404s) falls back to a drawn
 * card — gradient and food mark — rather than a broken frame.
 *
 * The clip list lives in `@/lib/landing/showcaseClips`.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { SHOWCASE_CLIPS, type ShowcaseClip } from '@/lib/landing/showcaseClips'

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
  registerVideo: (video: HTMLVideoElement) => void
  unregisterVideo: (video: HTMLVideoElement) => void
}

function ClipCard({ clip, registerVideo, unregisterVideo }: ClipCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [failed, setFailed] = useState(false)

  // Hands the element to the wall's observer, and takes it back when the card
  // swaps to the drawn fallback — otherwise the observer holds a detached node.
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    registerVideo(video)
    return () => unregisterVideo(video)
  }, [registerVideo, unregisterVideo, failed])

  const card = (
    <div
      className={`relative w-full overflow-hidden rounded-2xl ring-1 ring-white/10 shadow-[0_18px_44px_rgba(5,5,12,.5)] ${RATIO_CLASS[clip.ratio]}`}
      style={{ background: `linear-gradient(145deg, ${clip.from}, ${clip.to})` }}
    >
      {failed ? (
        /* No file uploaded yet — the card draws itself. */
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
      ) : (
        <video
          ref={videoRef}
          src={clip.src}
          poster={clip.poster}
          muted
          loop
          playsInline
          preload="none"
          disablePictureInPicture
          aria-hidden="true"
          onError={() => setFailed(true)}
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}

      {/* The business name, and nothing else. */}
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink-950/92 via-ink-950/55 to-transparent px-3.5 pb-3 pt-12 sm:px-4 sm:pb-4">
        <div className="font-geist text-sm font-bold uppercase leading-tight tracking-tight text-white sm:text-base">
          {clip.label}
        </div>
      </div>
    </div>
  )

  return (
    <div className="mb-3 break-inside-avoid sm:mb-4">
      {clip.href ? (
        <Link
          href={clip.href}
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-2xl transition-transform duration-300 hover:scale-[1.02] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-volt-400 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950"
        >
          {card}
        </Link>
      ) : (
        card
      )}
    </div>
  )
}

export default function LandingShowcase() {
  const videosRef = useRef<Set<HTMLVideoElement>>(new Set())
  const observerRef = useRef<IntersectionObserver | null>(null)
  const visibleRef = useRef<Set<HTMLVideoElement>>(new Set())
  const reducedMotion = usePrefersReducedMotion()

  // One observer for the whole wall: a card plays as it scrolls in and pauses
  // as it scrolls out, so only what is on screen is ever decoding.
  useEffect(() => {
    if (reducedMotion) {
      videosRef.current.forEach((video) => video.pause())
      return
    }

    const visible = visibleRef.current
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const video = entry.target as HTMLVideoElement
          if (entry.isIntersecting) {
            visible.add(video)
            // Autoplay can still be refused (data saver, low power mode); the
            // poster or the gradient underneath stays put when it is.
            void video.play().catch(() => {})
          } else {
            visible.delete(video)
            video.pause()
          }
        })
      },
      { rootMargin: '150px', threshold: 0.15 }
    )

    observerRef.current = observer
    videosRef.current.forEach((video) => observer.observe(video))

    return () => {
      observer.disconnect()
      observerRef.current = null
      visible.clear()
    }
  }, [reducedMotion])

  // A backgrounded tab keeps decoding otherwise.
  useEffect(() => {
    const sync = () => {
      if (document.visibilityState === 'visible') {
        if (reducedMotion) return
        visibleRef.current.forEach((video) => void video.play().catch(() => {}))
      } else {
        videosRef.current.forEach((video) => video.pause())
      }
    }

    document.addEventListener('visibilitychange', sync)
    return () => document.removeEventListener('visibilitychange', sync)
  }, [reducedMotion])

  const registerVideo = useCallback((video: HTMLVideoElement) => {
    videosRef.current.add(video)
    observerRef.current?.observe(video)
  }, [])

  const unregisterVideo = useCallback((video: HTMLVideoElement) => {
    videosRef.current.delete(video)
    visibleRef.current.delete(video)
    observerRef.current?.unobserve(video)
  }, [])

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
          Setiap satu dibina dari satu perbualan dalam Bahasa Melayu.
        </p>
      </div>

      {/* The wall — CSS columns, so cards of different heights stagger the way
          a masonry grid does without any measuring. */}
      <div className="relative mx-auto max-w-[1400px] px-3 sm:px-4">
        <div className="columns-2 gap-3 sm:gap-4 md:columns-3 lg:columns-4">
          {SHOWCASE_CLIPS.map((clip) => (
            <ClipCard
              key={clip.id}
              clip={clip}
              registerVideo={registerVideo}
              unregisterVideo={unregisterVideo}
            />
          ))}
        </div>
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

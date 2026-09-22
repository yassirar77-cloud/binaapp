'use client'

/**
 * The clip that plays behind the landing hero.
 *
 * Wallpaper, not content: it carries its own scrim, it is never announced to
 * a screen reader, and nothing in the hero above it depends on it having
 * loaded. Until the MP4 exists in `public/hero/` — or if it 404s, or the
 * browser refuses to decode it — this renders nothing at all and the hero
 * keeps the gradient it has always had. That is why it is safe to merge the
 * player before the footage.
 *
 * Unlike the showcase wall further down the page, this one is above the fold,
 * so it loads eagerly rather than waiting for an observer. It still stops
 * itself when the tab is hidden, when it scrolls away, and when the visitor
 * has asked for reduced motion or switched on data saver — a marketing hero
 * is not worth someone's battery or their data plan.
 */

import { useEffect, useRef, useState } from 'react'

const VIDEO_SRC = '/hero/binaapp-hero.mp4'
const POSTER_SRC = '/hero/binaapp-hero.jpg'

/** True when the visitor has asked for less motion, or their browser says the
 *  connection is metered or slow. Either way: hold on the poster. */
function useHoldStill() {
  const [hold, setHold] = useState(false)

  useEffect(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')

    const sync = () => {
      // `connection` is Chromium-only and every field is optional, so each
      // read is guarded rather than assumed.
      const connection = (navigator as Navigator & {
        connection?: { saveData?: boolean; effectiveType?: string }
      }).connection
      const thin =
        connection?.saveData === true ||
        connection?.effectiveType === 'slow-2g' ||
        connection?.effectiveType === '2g'

      setHold(motion.matches || thin)
    }

    sync()
    motion.addEventListener('change', sync)
    return () => motion.removeEventListener('change', sync)
  }, [])

  return hold
}

export default function LandingHeroVideo() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const sectionRef = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)
  const holdStill = useHoldStill()

  // Pause once the hero has scrolled past, and whenever the tab is hidden.
  useEffect(() => {
    const video = videoRef.current
    const section = sectionRef.current
    if (!video || !section || holdStill) return

    let onScreen = true

    const settle = () => {
      if (onScreen && document.visibilityState === 'visible') {
        // Autoplay can still be refused (low power mode, a browser policy);
        // the poster underneath stays put when it is.
        void video.play().catch(() => {})
      } else {
        video.pause()
      }
    }

    const observer = new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting
      settle()
    })
    observer.observe(section)
    document.addEventListener('visibilitychange', settle)
    settle()

    return () => {
      observer.disconnect()
      document.removeEventListener('visibilitychange', settle)
    }
  }, [holdStill])

  // No footage yet, or the browser cannot decode it — the hero's own gradient
  // is the fallback, so render nothing rather than a black rectangle.
  if (failed) return null

  return (
    <div ref={sectionRef} aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <video
        ref={videoRef}
        src={VIDEO_SRC}
        poster={POSTER_SRC}
        muted
        loop
        playsInline
        autoPlay={!holdStill}
        preload="metadata"
        disablePictureInPicture
        onError={() => setFailed(true)}
        className="absolute inset-0 h-full w-full object-cover"
      />

      {/* Scrims. Lighter than they look like they should be, because the
          clip is already graded down in the encode — the gradient over the
          headline is baked into the file. These only finish the job: a little
          overall weight, and a bottom edge that meets the section below
          without a seam. Stacking a full scrim on top of the grade turns the
          picture to mud. */}
      <div className="absolute inset-0 bg-ink-950/25" />
      <div className="absolute inset-0 bg-gradient-to-r from-ink-950/70 via-ink-950/30 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-b from-ink-950/50 via-transparent to-ink-950" />
    </div>
  )
}

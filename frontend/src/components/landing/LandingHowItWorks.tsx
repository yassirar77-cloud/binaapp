'use client'

/**
 * "Tengok cara ia berfungsi" — the 20-second film under the hero.
 *
 * One real merchant, Dapur Western Kak Mira, from sitting down with her phone
 * to showing the finished site to a customer. The middle of it is her own
 * screenshots and her own screen recording, so the words on screen are real.
 *
 * Nothing is laid over the picture. The film has its own text in it — her
 * brief, her menu, her site — and a caption on top would fight all of it. The
 * heading sits above the frame and stays there.
 *
 * Plays only while it is on screen: it is below the fold, it is three
 * megabytes, and a visitor who never scrolls this far should never pay for it.
 * `preload="none"` is what makes that true — without it the browser fetches
 * the file whatever the observer decides.
 */

import { useEffect, useRef, useState } from 'react'

const VIDEO_SRC = '/hero/binaapp-howitworks.mp4'
const POSTER_SRC = '/hero/binaapp-howitworks.jpg'

export default function LandingHowItWorks() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const frameRef = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const video = videoRef.current
    const frame = frameRef.current
    if (!video || !frame) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)')
    let onScreen = false

    const settle = () => {
      if (onScreen && document.visibilityState === 'visible' && !reduced.matches) {
        // Autoplay can still be refused (low power mode, a browser policy);
        // the poster stays put when it is.
        void video.play().catch(() => {})
      } else {
        video.pause()
      }
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        onScreen = entry.isIntersecting
        settle()
      },
      // A little early, so it is running by the time it is properly in view.
      { rootMargin: '100px', threshold: 0.25 }
    )
    observer.observe(frame)
    document.addEventListener('visibilitychange', settle)
    reduced.addEventListener('change', settle)

    return () => {
      observer.disconnect()
      document.removeEventListener('visibilitychange', settle)
      reduced.removeEventListener('change', settle)
    }
  }, [])

  // No film yet, or the browser cannot decode it — drop the section entirely
  // rather than leaving a heading over a black rectangle.
  if (failed) return null

  return (
    <section id="cara-ia-berfungsi" className="relative overflow-hidden bg-ink-950 py-16 lg:py-24">

      {/* Indigo glow behind the frame */}
      <div className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[820px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(79,61,255,.22),transparent_65%)]" />

      <div className="relative mx-auto mb-10 max-w-[760px] px-4 text-center sm:px-8 lg:mb-14">
        <h2 className="font-geist text-3xl font-extrabold leading-[1.08] tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl">
          Tengok cara ia berfungsi
        </h2>
      </div>

      {/* Full width, edge to edge. The film is 16:9; the box holds that shape
          so nothing jumps while it loads. */}
      <div ref={frameRef} className="relative w-full">
        <video
          ref={videoRef}
          src={VIDEO_SRC}
          poster={POSTER_SRC}
          muted
          loop
          playsInline
          preload="none"
          disablePictureInPicture
          aria-label="Dapur Western Kak Mira membina websitenya dengan BinaApp"
          onError={() => setFailed(true)}
          className="aspect-video w-full object-cover"
        />

        {/* Feathered top and bottom edges so the film meets the sections
            above and below without a hard seam. */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-ink-950 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-ink-950 to-transparent" />
      </div>
    </section>
  )
}

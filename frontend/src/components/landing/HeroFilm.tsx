'use client'

/**
 * The film in the hero: Dapur Western Kak Mira, from picking up her phone to
 * showing the finished site to a customer.
 *
 * Its own component rather than part of LandingHero, so the hero's copy — the
 * headline, the subtext, the one thing on this page anybody is meant to click —
 * stays server-rendered. Only the video needs to be interactive.
 *
 * It plays only while it is on screen. That matters more here than it did when
 * this sat below the fold: on a phone the card is under the headline and the
 * call to action, so a visitor who taps through without scrolling should never
 * pay for three megabytes. `preload="none"` is what makes that true — without
 * it the browser fetches the file whatever the observer decides.
 */

import { useEffect, useRef, useState } from 'react'

const VIDEO_SRC = '/hero/binaapp-howitworks.mp4'
const POSTER_SRC = '/hero/binaapp-howitworks.jpg'

/**
 * MEDIA_ERR_ABORTED. The browser gave up on a fetch it had started — which it
 * does routinely here, because `preload="none"` means the load only begins
 * when play() asks for it, and anything that pauses in the meantime cancels it.
 * It says nothing about whether the file can be played, and treating it as
 * fatal took the card off the page every time.
 */
const MEDIA_ERR_ABORTED = 1

export default function HeroFilm() {
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

  // No film on disk, or the browser cannot decode this one. The card goes;
  // the hero keeps its headline and its button, which are the parts that
  // matter. An aborted fetch is not that — see MEDIA_ERR_ABORTED above.
  if (failed) return null

  return (
    <div
      ref={frameRef}
      className="relative overflow-hidden rounded-2xl ring-1 ring-volt-400/15 shadow-[0_30px_80px_rgba(79,61,255,.4)]"
    >
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
        onError={() => {
          if (videoRef.current?.error?.code !== MEDIA_ERR_ABORTED) setFailed(true)
        }}
        className="aspect-video w-full object-cover"
      />
    </div>
  )
}

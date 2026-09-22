'use client'

/**
 * The film behind the hero: Dapur Western Kak Mira, from picking up her phone
 * to showing the finished site to a customer.
 *
 * Its own component rather than part of LandingHero, so the hero's copy — the
 * headline, the subtext, the one thing on this page anybody is meant to click —
 * stays server-rendered. Only the video needs to be interactive.
 *
 * It fills the section and is cropped to it, which on a phone means a 16:9
 * film in a tall box: roughly the middle quarter of each frame is what shows.
 * The film is framed for that — its subject sits near the centre of every shot.
 *
 * It plays only while the hero is on screen, and `preload="none"` means the
 * four megabytes are not fetched until it is. The poster covers the gap.
 */

import { useEffect, useRef, useState } from 'react'

const VIDEO_SRC = '/hero/binaapp-howitworks.mp4'
const POSTER_SRC = '/hero/binaapp-howitworks.jpg'

/**
 * MEDIA_ERR_ABORTED. The browser gave up on a fetch it had started — which it
 * does routinely here, because `preload="none"` means the load only begins
 * when play() asks for it, and anything that pauses in the meantime cancels it.
 * It says nothing about whether the file can be played, and treating it as
 * fatal took the film off the page every time.
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
      { rootMargin: '100px', threshold: 0.1 }
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

  // No film on disk, or the browser cannot decode this one. The layer goes and
  // the section's own gradient shows through, which is what the hero looked
  // like before there was a film. An aborted fetch is not that — see above.
  if (failed) return null

  return (
    <div ref={frameRef} className="absolute inset-0 z-0">
      <video
        ref={videoRef}
        src={VIDEO_SRC}
        poster={POSTER_SRC}
        muted
        loop
        playsInline
        preload="none"
        disablePictureInPicture
        aria-hidden="true"
        onError={() => {
          if (videoRef.current?.error?.code !== MEDIA_ERR_ABORTED) setFailed(true)
        }}
        className="h-full w-full object-cover"
      />
    </div>
  )
}

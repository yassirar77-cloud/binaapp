/**
 * Tiny dependency-free confetti burst for small "well done" moments.
 * Particles are plain fixed-position spans animated by CSS (see
 * `.cr-confetti` in app/create/create.css) and removed when finished.
 * Does nothing when the visitor prefers reduced motion.
 */
const COLORS = ['#C7FF3D', '#6B5CFF', '#FFB020', '#22C08F', '#F5F5FA']

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Burst `count` particles outward from a viewport point. */
export function burstConfetti(x: number, y: number, count = 14): void {
  if (typeof document === 'undefined' || prefersReducedMotion()) return
  const layer = document.createElement('div')
  layer.className = 'cr-confetti-layer'
  layer.setAttribute('aria-hidden', 'true')
  for (let i = 0; i < count; i++) {
    const p = document.createElement('span')
    p.className = 'cr-confetti'
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.5
    const dist = 36 + Math.random() * 54
    p.style.left = `${x}px`
    p.style.top = `${y}px`
    p.style.background = COLORS[i % COLORS.length]
    p.style.setProperty('--dx', `${Math.cos(angle) * dist}px`)
    p.style.setProperty('--dy', `${Math.sin(angle) * dist - 24}px`)
    p.style.setProperty('--rot', `${Math.round(Math.random() * 540 - 270)}deg`)
    if (i % 3 === 0) p.style.borderRadius = '50%'
    layer.appendChild(p)
  }
  document.body.appendChild(layer)
  window.setTimeout(() => layer.remove(), 1000)
}

/** Burst from the centre of an element, if it is on screen. */
export function burstFrom(el: Element | null | undefined, count?: number): boolean {
  if (!el) return false
  const r = el.getBoundingClientRect()
  if (!r.width || r.bottom < 0 || r.top > window.innerHeight || r.right < 0 || r.left > window.innerWidth) return false
  burstConfetti(r.left + r.width / 2, r.top + r.height / 2, count)
  return true
}

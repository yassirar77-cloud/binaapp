'use client'

import { useRef, useEffect } from 'react'

interface ParticleGlobeProps {
  isVisible: boolean
}

export default function ParticleGlobe({ isVisible }: ParticleGlobeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  useEffect(() => {
    if (!isVisible) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    const w = rect.width
    const h = rect.height
    const NUM = 800
    const radius = 0.35 * Math.min(w, h)

    const particles: { theta: number; phi: number }[] = []
    for (let i = 0; i < NUM; i++) {
      particles.push({
        theta: Math.random() * Math.PI * 2,
        phi: Math.acos(2 * Math.random() - 1),
      })
    }

    let angle = 0

    function draw() {
      if (!ctx) return
      ctx.clearRect(0, 0, w, h)

      // Background gradient
      const bg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.6)
      bg.addColorStop(0, 'rgba(30,60,120,0.15)')
      bg.addColorStop(1, 'transparent')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, w, h)

      angle += 0.004

      for (const p of particles) {
        const x3d = radius * Math.sin(p.phi) * Math.cos(p.theta + angle)
        const y3d = radius * Math.cos(p.phi)
        const z3d = radius * Math.sin(p.phi) * Math.sin(p.theta + angle)

        const perspective = 1 / (1 - z3d / (radius * 3))
        const x2d = w / 2 + x3d * perspective
        const y2d = h / 2 + y3d * perspective

        const depth = (z3d + radius) / (2 * radius)
        const size = 0.5 + depth * 1.5
        const alpha = 0.1 + depth * 0.6

        const hue = 200 + depth * 30
        ctx.beginPath()
        ctx.arc(x2d, y2d, size * perspective, 0, Math.PI * 2)
        ctx.fillStyle = `hsla(${hue}, 80%, 65%, ${alpha})`
        ctx.fill()
      }

      animRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animRef.current)
    }
  }, [isVisible])

  return (
    <div className="w-full h-full relative" style={{ background: '#0a0a1a' }}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ display: 'block' }}
      />
      <div className="absolute bottom-3 left-0 right-0 text-center">
        <span className="text-[10px] font-medium tracking-widest uppercase" style={{ color: 'rgba(100,160,255,0.6)' }}>
          Premium Globe
        </span>
      </div>
    </div>
  )
}

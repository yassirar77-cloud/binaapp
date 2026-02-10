'use client'

import { useRef, useEffect } from 'react'

interface MatrixCodeProps {
  isVisible: boolean
}

export default function MatrixCode({ isVisible }: MatrixCodeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
    const chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノ0123456789ABCDEF'
    const fontSize = 12
    const columns = Math.floor(w / fontSize)
    const drops = Array(columns).fill(1)

    function draw() {
      if (!ctx) return
      ctx.fillStyle = 'rgba(2,12,2,0.08)'
      ctx.fillRect(0, 0, w, h)

      ctx.fillStyle = '#34d399'
      ctx.font = `${fontSize}px monospace`

      for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)]
        ctx.fillText(text, i * fontSize, drops[i] * fontSize)
        if (drops[i] * fontSize > h && Math.random() > 0.975) {
          drops[i] = 0
        }
        drops[i]++
      }
    }

    intervalRef.current = setInterval(draw, 50)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isVisible])

  return (
    <div className="w-full h-full relative" style={{ background: '#020c02' }}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ display: 'block' }}
      />
      {/* Radial fade overlay */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 30%, rgba(2,12,2,0.8) 100%)',
        }}
      />
      {/* Text overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
        <p
          className="font-mono text-xs font-bold tracking-wider"
          style={{ color: '#34d399', textShadow: '0 0 8px rgba(52,211,153,0.5)' }}
        >
          {'// ORDER NOW'}
        </p>
      </div>
    </div>
  )
}

'use client'

import { useMemo } from 'react'

export default function ParallaxLayers() {
  const circles = useMemo(() => {
    return Array.from({ length: 12 }, (_, i) => ({
      size: 20 + Math.random() * 50,
      left: `${10 + Math.random() * 80}%`,
      top: `${10 + Math.random() * 80}%`,
      borderColor: `rgba(${180 + Math.random() * 75}, ${80 + Math.random() * 80}, ${200 + Math.random() * 55}, ${0.15 + Math.random() * 0.2})`,
      fillColor: `rgba(${180 + Math.random() * 75}, ${80 + Math.random() * 80}, ${200 + Math.random() * 55}, 0.05)`,
      duration: `${4 + Math.random() * 4}s`,
      delay: `${Math.random() * 3}s`,
      yOffset: 8 + Math.random() * 15,
    }))
  }, [])

  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #12061f 0%, #0a0a1a 50%, #120a1f 100%)' }}>
      {circles.map((c, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            width: `${c.size}px`,
            height: `${c.size}px`,
            left: c.left,
            top: c.top,
            border: `1px solid ${c.borderColor}`,
            background: c.fillColor,
            animation: `parallaxFloat ${c.duration} ease-in-out infinite`,
            animationDelay: c.delay,
            ['--y-offset' as string]: `${c.yOffset}px`,
          }}
        />
      ))}

      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
        <span
          className="text-lg font-bold tracking-wide italic"
          style={{
            background: 'linear-gradient(135deg, #ec4899, #8b5cf6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Elegance
        </span>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes parallaxFloat {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(calc(var(--y-offset, 10px) * -1)); }
        }
      `}} />
    </div>
  )
}

'use client'

import { useMemo, useEffect, useRef } from 'react'

export default function WordExplosion() {
  const containerRef = useRef<HTMLDivElement>(null)

  const words = useMemo(() => {
    const text = 'Warung Selera Nasi Lemak Ayam Goreng Rempah Sambal Pedas Sedap'
    return text.split(' ').map((word, i) => {
      const angles = [
        { x: -120, y: -80, rot: -540 },
        { x: 120, y: -60, rot: 480 },
        { x: -100, y: 80, rot: 360 },
        { x: 100, y: 60, rot: -400 },
        { x: 0, y: -100, rot: 720 },
        { x: 0, y: 100, rot: -600 },
        { x: -130, y: 0, rot: 500 },
        { x: 130, y: 0, rot: -450 },
      ]
      const angle = angles[Math.floor(Math.random() * angles.length)]
      return {
        text: word,
        startX: angle.x,
        startY: angle.y,
        startRot: angle.rot,
        startScale: 0.1 + Math.random() * 0.2,
        delay: i * 0.12 + Math.random() * 0.1,
        duration: 0.8 + Math.random() * 0.5,
        finalX: 10 + (i % 4) * 22,
        finalY: 35 + Math.floor(i / 4) * 18,
        size: i < 2 ? 18 : 12,
        bold: i < 2,
      }
    })
  }, [])

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative overflow-hidden"
      style={{ background: '#FFF8F0' }}
    >
      {words.map((w, i) => (
        <span
          key={i}
          className="absolute font-semibold"
          style={{
            left: `${w.finalX}%`,
            top: `${w.finalY}%`,
            fontSize: `${w.size}px`,
            fontWeight: w.bold ? 700 : 500,
            color: i % 3 === 0 ? '#E85D3A' : i % 3 === 1 ? '#D4A853' : '#1A1A1A',
            opacity: 0,
            animation: `wordFlyIn ${w.duration}s ${w.delay}s cubic-bezier(0.23, 1, 0.32, 1) forwards`,
            ['--start-x' as string]: `${w.startX}px`,
            ['--start-y' as string]: `${w.startY}px`,
            ['--start-rot' as string]: `${w.startRot}deg`,
            ['--start-scale' as string]: w.startScale,
          }}
        >
          {w.text}
        </span>
      ))}

      {/* Label */}
      <div className="absolute bottom-3 left-0 right-0 text-center z-10">
        <span
          className="text-[10px] font-medium tracking-widest uppercase"
          style={{ color: 'rgba(232,93,58,0.5)' }}
        >
          Letupan Kata
        </span>
      </div>

      <style
        dangerouslySetInnerHTML={{
          __html: `
        @keyframes wordFlyIn {
          0% {
            opacity: 0;
            transform: translate(var(--start-x), var(--start-y)) rotate(var(--start-rot)) scale(var(--start-scale));
            filter: blur(6px);
          }
          60% { opacity: 1; filter: blur(0px); }
          80% { transform: translate(0, 0) rotate(0deg) scale(1.08); }
          100% { opacity: 1; transform: translate(0, 0) rotate(0deg) scale(1); filter: blur(0px); }
        }
      `,
        }}
      />
    </div>
  )
}

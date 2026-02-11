'use client'

import { useState, useEffect, useRef } from 'react'

export default function GhostRestaurant() {
  const [phase, setPhase] = useState<'visible' | 'vanishing' | 'invisible' | 'appearing'>('visible')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    function cycle() {
      // Visible for 2s (shortened for preview card)
      timerRef.current = setTimeout(() => {
        setPhase('vanishing')
        // Vanish transition takes 1s
        timerRef.current = setTimeout(() => {
          setPhase('invisible')
          // Invisible for 1.5s
          timerRef.current = setTimeout(() => {
            setPhase('appearing')
            // Appear transition takes 1.5s
            timerRef.current = setTimeout(() => {
              setPhase('visible')
              cycle()
            }, 1500)
          }, 1500)
        }, 1000)
      }, 2000)
    }
    cycle()
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  const isHidden = phase === 'vanishing' || phase === 'invisible'

  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: '#0D0D0D' }}>
      {/* Timer bar at top */}
      <div
        className="absolute top-0 left-0 h-[2px] z-20"
        style={{
          width: phase === 'visible' || phase === 'appearing' ? '100%' : '0%',
          background: 'linear-gradient(90deg, #00E5A0, #00B8D4)',
          boxShadow: '0 0 10px rgba(0,229,160,0.5)',
          transition: phase === 'vanishing' ? 'width 1s ease-out' : 'none',
        }}
      />

      {/* Site content preview */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center px-4"
        style={{
          opacity: phase === 'vanishing' || phase === 'invisible' ? 0 : 1,
          filter:
            phase === 'vanishing'
              ? 'blur(15px) brightness(2)'
              : phase === 'appearing'
                ? 'blur(0px) brightness(1)'
                : 'none',
          transform: phase === 'vanishing' ? 'scale(0.97)' : 'scale(1)',
          transition: 'opacity 1s, filter 1s, transform 1s',
        }}
      >
        <div
          className="text-center"
          style={{ fontFamily: "'Cormorant Garamond', serif" }}
        >
          <div className="text-[10px] tracking-[0.2em] uppercase mb-1" style={{ color: '#00E5A0' }}>
            Dapur Rahsia
          </div>
          <div className="text-lg font-bold" style={{ color: '#EAEAEA' }}>
            Restoran Hantu
          </div>
          <div className="text-[9px] mt-1" style={{ color: '#8A8A8A' }}>
            Rendang Misteri &bull; Nasi Bayangan
          </div>
        </div>
        {/* Fake menu cards */}
        <div className="flex gap-2 mt-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="rounded-lg"
              style={{
                width: 40,
                height: 28,
                background: 'rgba(30,30,30,0.8)',
                border: '1px solid rgba(0,229,160,0.15)',
              }}
            />
          ))}
        </div>
      </div>

      {/* Ghost overlay */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center z-10"
        style={{
          opacity: isHidden ? 1 : 0,
          transition: 'opacity 0.5s',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            fontSize: 36,
            animation: 'ghostBob 2s ease-in-out infinite',
          }}
        >
          👻
        </div>
        <div className="text-[11px] mt-1 font-medium" style={{ color: '#00E5A0' }}>
          Gone Invisible...
        </div>
      </div>

      {/* Label */}
      <div className="absolute bottom-3 left-0 right-0 text-center z-10">
        <span
          className="text-[10px] font-medium tracking-widest uppercase"
          style={{ color: 'rgba(0,229,160,0.5)' }}
        >
          Restoran Hantu
        </span>
      </div>

      <style
        dangerouslySetInnerHTML={{
          __html: `
        @keyframes ghostBob {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
      `,
        }}
      />
    </div>
  )
}

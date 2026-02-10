'use client'

import { useMemo } from 'react'

export default function Aurora() {
  const stars = useMemo(() => {
    return Array.from({ length: 45 }, (_, i) => ({
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      size: 1 + Math.random() * 1.5,
      delay: `${Math.random() * 3}s`,
      duration: `${2 + Math.random() * 2}s`,
    }))
  }, [])

  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: '#050520' }}>
      {/* Stars */}
      {stars.map((star, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            left: star.left,
            top: star.top,
            width: `${star.size}px`,
            height: `${star.size}px`,
            background: 'white',
            animation: `twinkle ${star.duration} ease-in-out infinite`,
            animationDelay: star.delay,
          }}
        />
      ))}

      {/* Aurora bands */}
      <div
        className="absolute"
        style={{
          top: '15%',
          left: '-20%',
          width: '140%',
          height: '40%',
          background: 'linear-gradient(90deg, transparent, rgba(52,211,153,0.3), rgba(74,158,255,0.2), transparent)',
          filter: 'blur(50px)',
          animation: 'auroraFlow 8s ease-in-out infinite',
        }}
      />
      <div
        className="absolute"
        style={{
          top: '25%',
          left: '-10%',
          width: '120%',
          height: '30%',
          background: 'linear-gradient(90deg, transparent, rgba(139,92,246,0.25), rgba(52,211,153,0.2), transparent)',
          filter: 'blur(50px)',
          animation: 'auroraFlow 10s ease-in-out infinite 2s',
        }}
      />
      <div
        className="absolute"
        style={{
          top: '10%',
          left: '-15%',
          width: '130%',
          height: '35%',
          background: 'linear-gradient(90deg, transparent, rgba(236,72,153,0.15), rgba(139,92,246,0.15), transparent)',
          filter: 'blur(50px)',
          animation: 'auroraFlow 12s ease-in-out infinite 4s',
        }}
      />

      {/* Label */}
      <div className="absolute bottom-3 left-0 right-0 text-center z-10">
        <span className="text-[10px] font-medium tracking-widest uppercase" style={{ color: 'rgba(52,211,153,0.5)' }}>
          Alam Semula Jadi
        </span>
      </div>

      <style jsx>{`
        @keyframes auroraFlow {
          0%, 100% { transform: translateX(-10%) skewY(-5deg) scaleY(1); }
          33% { transform: translateX(10%) skewY(3deg) scaleY(1.3); }
          66% { transform: translateX(-5%) skewY(-2deg) scaleY(0.8); }
        }
        @keyframes twinkle {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  )
}

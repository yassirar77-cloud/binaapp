'use client'

const FOOD_ITEMS = [
  { emoji: '🍔', x: '15%', delay: '0s', duration: '3s', rot: '-5deg' },
  { emoji: '🍕', x: '75%', delay: '0.5s', duration: '3.5s', rot: '5deg' },
  { emoji: '🍜', x: '45%', delay: '1s', duration: '4s', rot: '-3deg' },
  { emoji: '🧋', x: '85%', delay: '0.3s', duration: '3.2s', rot: '4deg' },
  { emoji: '🍛', x: '30%', delay: '0.7s', duration: '3.8s', rot: '-4deg' },
  { emoji: '🥤', x: '60%', delay: '1.2s', duration: '3.6s', rot: '3deg' },
]

export default function FloatingFood() {
  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #1a1025 0%, #0f1729 100%)' }}>
      {FOOD_ITEMS.map((item, i) => (
        <div
          key={i}
          className="absolute flex items-center justify-center"
          style={{
            left: item.x,
            top: `${20 + (i % 3) * 25}%`,
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'rgba(255,255,255,0.08)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.12)',
            animation: `floatUp ${item.duration} ease-in-out infinite`,
            animationDelay: item.delay,
            ['--rot' as string]: item.rot,
          }}
        >
          <span className="text-lg">{item.emoji}</span>
        </div>
      ))}

      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
        <p className="text-white/80 font-semibold text-xs tracking-wide">Menu Pilihan</p>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes floatUp {
          0%, 100% { transform: translateY(0) rotate(var(--rot, 0deg)); }
          50% { transform: translateY(-15px) rotate(calc(var(--rot, 0deg) + 2deg)); }
        }
      `}} />
    </div>
  )
}

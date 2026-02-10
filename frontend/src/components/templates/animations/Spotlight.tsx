'use client'

const ICONS = [
  { emoji: '🍽️', delay: '0s' },
  { emoji: '📦', delay: '0.3s' },
  { emoji: '🛵', delay: '0.6s' },
]

export default function Spotlight() {
  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: '#0a0a14' }}>
      {/* Cross pattern background */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.8) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      />

      {/* Moving spotlight */}
      <div
        className="absolute"
        style={{
          width: '150px',
          height: '150px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,107,53,0.25) 0%, transparent 70%)',
          animation: 'spotlightMove 8s ease-in-out infinite',
        }}
      />

      {/* Icon circles */}
      <div className="absolute inset-0 flex items-center justify-center gap-5 z-10">
        {ICONS.map((icon, i) => (
          <div
            key={i}
            className="flex items-center justify-center"
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              border: '1px solid rgba(255,107,53,0.3)',
              background: 'rgba(255,107,53,0.05)',
              animation: 'iconPulse 2s ease-in-out infinite',
              animationDelay: icon.delay,
            }}
          >
            <span className="text-base">{icon.emoji}</span>
          </div>
        ))}
      </div>

      {/* Text */}
      <div className="absolute bottom-4 left-0 right-0 text-center z-10">
        <span className="text-[10px] font-medium tracking-wider" style={{ color: 'rgba(255,107,53,0.5)' }}>
          Pesan • Bayar • Hantar
        </span>
      </div>

      <style jsx>{`
        @keyframes spotlightMove {
          0% { top: 10%; left: 10%; }
          25% { top: 10%; left: 60%; }
          50% { top: 50%; left: 50%; }
          75% { top: 30%; left: 10%; }
          100% { top: 10%; left: 10%; }
        }
        @keyframes iconPulse {
          0%, 100% { transform: scale(1); opacity: 0.7; }
          50% { transform: scale(1.1); opacity: 1; }
        }
      `}</style>
    </div>
  )
}

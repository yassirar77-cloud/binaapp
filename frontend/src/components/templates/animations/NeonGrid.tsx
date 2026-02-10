'use client'

export default function NeonGrid() {
  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: '#000000' }}>
      {/* Perspective grid */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            'linear-gradient(rgba(74,158,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(74,158,255,0.08) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          animation: 'gridMove 3s linear infinite',
          transform: 'perspective(500px) rotateX(60deg)',
          transformOrigin: 'center top',
        }}
      />

      {/* Blue glow orb */}
      <div
        className="absolute rounded-full"
        style={{
          width: '120px',
          height: '120px',
          top: '20%',
          left: '20%',
          background: 'radial-gradient(circle, rgba(74,158,255,0.25) 0%, transparent 70%)',
          animation: 'pulseGlow 4s ease-in-out infinite',
        }}
      />

      {/* Purple glow orb */}
      <div
        className="absolute rounded-full"
        style={{
          width: '100px',
          height: '100px',
          top: '30%',
          right: '15%',
          background: 'radial-gradient(circle, rgba(139,92,246,0.2) 0%, transparent 70%)',
          animation: 'pulseGlow 4s ease-in-out infinite 2s',
        }}
      />

      {/* Neon text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
        <p
          className="font-bold text-sm tracking-[0.2em] uppercase"
          style={{
            color: '#4a9eff',
            textShadow: '0 0 10px rgba(74,158,255,0.5), 0 0 20px rgba(74,158,255,0.3), 0 0 40px rgba(74,158,255,0.15)',
          }}
        >
          RESTORAN
        </p>
        <p className="text-[10px] mt-1" style={{ color: 'rgba(74,158,255,0.4)' }}>
          Order Online
        </p>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes gridMove {
          0% { background-position: 0 0; }
          100% { background-position: 0 40px; }
        }
        @keyframes pulseGlow {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.2); }
        }
      `}} />
    </div>
  )
}

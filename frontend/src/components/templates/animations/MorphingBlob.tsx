'use client'

export default function MorphingBlob() {
  return (
    <div className="w-full h-full relative overflow-hidden flex items-center justify-center" style={{ background: '#0a0a14' }}>
      {/* Blurred glow behind */}
      <div
        className="absolute"
        style={{
          width: '140px',
          height: '140px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #f97316, #ec4899, #8b5cf6)',
          filter: 'blur(40px)',
          opacity: 0.35,
          animation: 'blobMorph 8s ease-in-out infinite',
        }}
      />

      {/* Main blob */}
      <div
        style={{
          width: '100px',
          height: '100px',
          background: 'linear-gradient(135deg, #f97316, #ec4899, #8b5cf6)',
          animation: 'blobMorph 8s ease-in-out infinite',
          borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%',
        }}
      />

      {/* Label */}
      <div className="absolute bottom-4 left-0 right-0 text-center">
        <span className="text-[10px] font-medium tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.4)' }}>
          MENU KAMI
        </span>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes blobMorph {
          0%   { border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; }
          25%  { border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%; }
          50%  { border-radius: 50% 60% 30% 60% / 30% 70% 50% 60%; }
          75%  { border-radius: 60% 30% 60% 40% / 70% 50% 40% 60%; }
          100% { border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; }
        }
      `}} />
    </div>
  )
}

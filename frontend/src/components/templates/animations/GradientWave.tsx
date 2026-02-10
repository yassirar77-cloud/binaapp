'use client'

export default function GradientWave() {
  return (
    <div className="w-full h-full relative overflow-hidden" style={{ background: 'linear-gradient(135deg, #1a0533 0%, #0d1b3e 50%, #1a0533 100%)' }}>
      {/* Wave layers */}
      <svg className="absolute bottom-0 left-0 w-[200%] h-[60%]" style={{ animation: 'waveSlide 6s linear infinite', opacity: 0.4 }} viewBox="0 0 1200 200" preserveAspectRatio="none">
        <path d="M0,100 C200,40 400,160 600,100 C800,40 1000,160 1200,100 L1200,200 L0,200 Z" fill="url(#wave1)" />
        <defs>
          <linearGradient id="wave1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#ec4899" />
          </linearGradient>
        </defs>
      </svg>
      <svg className="absolute bottom-0 left-0 w-[200%] h-[45%]" style={{ animation: 'waveSlide 8s linear infinite reverse', opacity: 0.25 }} viewBox="0 0 1200 200" preserveAspectRatio="none">
        <path d="M0,120 C150,60 350,180 600,120 C850,60 1050,180 1200,120 L1200,200 L0,200 Z" fill="url(#wave2)" />
        <defs>
          <linearGradient id="wave2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
        </defs>
      </svg>
      <svg className="absolute bottom-0 left-0 w-[200%] h-[35%]" style={{ animation: 'waveSlide 10s linear infinite', opacity: 0.15 }} viewBox="0 0 1200 200" preserveAspectRatio="none">
        <path d="M0,140 C300,80 500,200 700,140 C900,80 1100,200 1200,140 L1200,200 L0,200 Z" fill="url(#wave3)" />
        <defs>
          <linearGradient id="wave3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ec4899" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
      </svg>

      {/* Text overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
        <p className="text-white/90 font-bold text-sm tracking-wide">Restoran Anda</p>
        <p className="text-white/50 text-[10px] mt-1">Rasa yang tidak terlupa</p>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes waveSlide {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}} />
    </div>
  )
}

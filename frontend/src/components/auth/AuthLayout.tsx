interface AuthLayoutProps {
  children: React.ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="relative min-h-screen flex items-center justify-center bg-oat-50 px-4 py-12 overflow-hidden">

      {/* Dot grid — same as LandingHero */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(20,20,19,.05) 1px, transparent 0)',
          backgroundSize: '36px 36px',
          maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse at center, black 30%, transparent 75%)',
        }}
      />

      {/* Terracotta wash — center */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-[radial-gradient(circle,rgba(217,119,87,.10),transparent_65%)] pointer-events-none" />

      {/* Warm cream wash — bottom right */}
      <div className="absolute -bottom-[120px] -right-[80px] w-[400px] h-[400px] rounded-full bg-[radial-gradient(circle,rgba(222,219,207,.6),transparent_65%)] pointer-events-none" />

      {/* Content */}
      <div className="relative w-full max-w-[420px]">
        {children}
      </div>
    </div>
  )
}

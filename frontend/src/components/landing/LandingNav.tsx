'use client'

import Link from 'next/link'
import Image from 'next/image'

interface LandingNavProps {
  user: any
  loading: boolean
  onLogout: () => void
}

export default function LandingNav({ user, loading, onLogout }: LandingNavProps) {
  return (
    <nav className="sticky top-0 z-50 bg-oat-50/[.85] backdrop-blur-xl border-b border-carbon-900/[.08]">
      <div className="max-w-[1200px] mx-auto px-4 sm:px-8 py-3.5 flex items-center justify-between">

        {/* Logo — links to homepage */}
        <Link href="/" className="flex items-center gap-2.5">
          <Image
            src="/brand/logo-mark.svg"
            alt="BinaApp"
            width={30}
            height={30}
            className="rounded-lg"
          />
          <span className="font-geist font-bold text-base sm:text-lg text-carbon-900 tracking-tight">
            bina<span className="text-clay-500">app</span>
          </span>
        </Link>

        {/* Nav links — desktop only */}
        <div className="hidden md:flex gap-7 font-geist text-sm text-carbon-400">
          <a href="#ciri" className="text-carbon-900 font-medium hover:text-clay-600 transition-colors">
            Ciri-ciri
          </a>
          <a href="#harga" className="hover:text-carbon-900 transition-colors">
            Harga
          </a>
        </div>

        {/* Auth buttons */}
        <div className="flex items-center gap-2">
          {!loading && (
            user ? (
              <>
                <Link
                  href="/dashboard"
                  className="font-geist text-sm text-carbon-400 hover:text-carbon-900 transition-colors px-3 py-2"
                >
                  Website Saya
                </Link>
                <button
                  onClick={onLogout}
                  className="font-geist text-sm text-carbon-400 hover:text-carbon-900 transition-colors px-3 py-2"
                >
                  Log Keluar
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden sm:inline font-geist text-sm text-carbon-900 px-3.5 py-2 hover:text-carbon-500 transition-colors"
                >
                  Log Masuk
                </Link>
                <Link
                  href="/register"
                  className="font-geist font-semibold text-sm text-white bg-clay-500 px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-xl shadow-card-warm hover:bg-clay-600 transition-colors tracking-tight"
                >
                  <span className="sm:hidden">Percuma →</span>
                  <span className="hidden sm:inline">Mula Percuma →</span>
                </Link>
              </>
            )
          )}
        </div>
      </div>
    </nav>
  )
}

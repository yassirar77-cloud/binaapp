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
    <nav className="sticky top-0 z-50 bg-ink-900/[.78] backdrop-blur-xl border-b border-white/[.06]">
      <div className="max-w-[1200px] mx-auto px-8 py-3.5 flex items-center justify-between">

        {/* Logo — links to homepage */}
        <Link href="/" className="flex items-center gap-2.5">
          <Image
            src="/brand/logo-mark.svg"
            alt="BinaApp"
            width={30}
            height={30}
            className="rounded-lg"
          />
          <span className="font-geist font-bold text-lg text-white tracking-tight">
            bina<span className="text-brand-300">app</span>
          </span>
        </Link>

        {/* Nav links — desktop only */}
        <div className="hidden md:flex gap-7 font-geist text-sm text-ink-300">
          <a href="#ciri" className="text-white font-medium hover:text-white transition-colors">
            Ciri-ciri
          </a>
          <a href="#harga" className="hover:text-white transition-colors">
            Harga
          </a>
        </div>

        {/* Auth buttons */}
        <div className="flex items-center gap-2">
          {!loading && (
            user ? (
              <>
                <Link
                  href="/my-projects"
                  className="font-geist text-sm text-ink-300 hover:text-white transition-colors px-3 py-2"
                >
                  Website Saya
                </Link>
                <button
                  onClick={onLogout}
                  className="font-geist text-sm text-ink-300 hover:text-white transition-colors px-3 py-2"
                >
                  Log Keluar
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="font-geist text-sm text-white px-3.5 py-2 hover:text-ink-300 transition-colors"
                >
                  Log Masuk
                </Link>
                <Link
                  href="/register"
                  className="font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-2.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 transition-colors tracking-tight"
                >
                  Mula Percuma →
                </Link>
              </>
            )
          )}
        </div>
      </div>
    </nav>
  )
}

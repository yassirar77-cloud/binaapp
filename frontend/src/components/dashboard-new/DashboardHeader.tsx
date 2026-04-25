'use client'

import { useState } from 'react'

interface NavItem {
  label: string
  href: string
  active?: boolean
  badge?: number
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Papan Pemuka', href: '/dashboard', active: true },
  { label: 'Website Saya', href: '/websites' },
  { label: 'Pesanan', href: '/orders', badge: 3 },
  { label: 'Penghantar', href: '/delivery' },
  { label: 'Menu', href: '/menu' },
  { label: 'Analitik', href: '/analytics' },
]

interface DashboardHeaderProps {
  /** Number of unread notifications */
  notificationCount?: number
  /** User display name for avatar fallback */
  userName?: string
  /** User avatar URL */
  avatarUrl?: string
  /** New orders count for badge on Pesanan nav */
  newOrdersCount?: number
}

export default function DashboardHeader({
  notificationCount = 0,
  userName = 'Pengguna',
  avatarUrl,
  newOrdersCount,
}: DashboardHeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [avatarMenuOpen, setAvatarMenuOpen] = useState(false)

  const navItems = NAV_ITEMS.map((item) =>
    item.href === '/orders' && newOrdersCount !== undefined
      ? { ...item, badge: newOrdersCount }
      : item
  )

  const initials = userName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <header className="dash-glass sticky top-0 z-50 border-b border-white/[0.08]">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 lg:px-6">
        {/* Left — Logo */}
        <a href="/dashboard" className="flex items-center gap-2 shrink-0">
          <img
            src="/brand/logo-mark.svg"
            alt="BinaApp"
            className="h-7 w-7"
          />
          <span className="text-sm font-semibold text-white tracking-tight hidden sm:inline">
            binaapp
          </span>
        </a>

        {/* Center — Desktop pill nav */}
        <nav className="hidden md:flex items-center gap-0.5 rounded-full bg-white/[0.05] p-1">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={`
                relative rounded-full px-3 py-1.5 text-xs font-medium transition-colors
                ${
                  item.active
                    ? 'bg-white/[0.1] text-white'
                    : 'text-white/50 hover:text-white/80'
                }
              `}
            >
              {item.label}
              {item.badge && item.badge > 0 ? (
                <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[#C7FF3D] px-1 text-[10px] font-bold text-[#0B0B15]">
                  {item.badge}
                </span>
              ) : null}
            </a>
          ))}
        </nav>

        {/* Right — Actions */}
        <div className="flex items-center gap-3">
          {/* Search placeholder */}
          <button className="hidden lg:flex items-center gap-2 rounded-lg bg-white/[0.05] border border-white/[0.08] px-3 py-1.5 text-xs text-white/40 hover:bg-white/[0.08] transition-colors">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Cari...
            <kbd className="ml-2 rounded border border-white/[0.12] bg-white/[0.05] px-1 py-0.5 text-[10px] text-white/30">
              ⌘K
            </kbd>
          </button>

          {/* Notification bell */}
          <button className="relative rounded-lg p-2 text-white/50 hover:text-white hover:bg-white/[0.05] transition-colors">
            <svg className="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
            {notificationCount > 0 && (
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#C7FF3D]" />
            )}
          </button>

          {/* Avatar dropdown */}
          <div className="relative">
            <button
              onClick={() => setAvatarMenuOpen(!avatarMenuOpen)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-white/[0.1] text-xs font-semibold text-white hover:bg-white/[0.15] transition-colors overflow-hidden"
            >
              {avatarUrl ? (
                <img src={avatarUrl} alt={userName} className="h-full w-full object-cover" />
              ) : (
                initials
              )}
            </button>

            {avatarMenuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setAvatarMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-2 z-50 w-44 rounded-xl bg-[#161623] border border-white/[0.08] py-1.5 shadow-xl shadow-black/40">
                  {[
                    { label: 'Profil', href: '/profile' },
                    { label: 'Langganan', href: '/subscription' },
                    { label: 'Log Keluar', href: '/logout' },
                  ].map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      className="block px-4 py-2 text-sm text-white/70 hover:text-white hover:bg-white/[0.05] transition-colors"
                    >
                      {item.label}
                    </a>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden rounded-lg p-2 text-white/50 hover:text-white hover:bg-white/[0.05] transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile nav drawer */}
      {mobileMenuOpen && (
        <nav className="md:hidden border-t border-white/[0.06] px-4 pb-4 pt-2">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={`
                flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition-colors
                ${item.active ? 'text-white bg-white/[0.06]' : 'text-white/50 hover:text-white'}
              `}
            >
              {item.label}
              {item.badge && item.badge > 0 ? (
                <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#C7FF3D] px-1.5 text-[11px] font-bold text-[#0B0B15]">
                  {item.badge}
                </span>
              ) : null}
            </a>
          ))}
        </nav>
      )}
    </header>
  )
}

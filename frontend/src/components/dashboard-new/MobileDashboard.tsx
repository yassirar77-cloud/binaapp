'use client'

import { useState, ReactNode } from 'react'
import DashboardGreeting from './DashboardGreeting'
import ActionCard from './ActionCard'
import WebsiteCard, { WebsiteStatus } from './WebsiteCard'
import ActivityFeed, { ActivityEvent } from './ActivityFeed'
import { UsageWidget } from '@/components/UsageWidget'

/* ── Shared types ── */

export interface WebsiteItem {
  id: string
  name: string
  subdomain: string
  status: WebsiteStatus
  templateImage?: string
  orders: number
  views: string
}

export interface MobileActionItem {
  icon: ReactNode
  title: string
  description: string
  meta: { dotColor: string; label: string; pulse?: boolean }
  hue: string
  href: string
  featured?: boolean
}

export interface MobileStat {
  label: string
  value: string
  delta?: { text: string; color: string; icon?: 'up' | 'down' }
  featured?: boolean
  pulse?: boolean
}

/* ── Nav items ── */

const NAV_ITEMS: { label: string; href: string; active?: boolean; hasBadge?: boolean }[] = [
  { label: 'Papan Pemuka', href: '/dashboard', active: true },
  { label: 'Website Saya', href: '/websites' },
  { label: 'Pesanan', href: '/orders', hasBadge: true },
  { label: 'Penghantar', href: '/delivery' },
  { label: 'Menu', href: '/menu' },
  { label: 'Analitik', href: '/analytics' },
]

const ACCOUNT_ITEMS = [
  { label: 'Profil', href: '/profile' },
  { label: 'Langganan', href: '/subscription' },
] as const

/* ── Props ── */

interface MobileDashboardProps {
  userName: string
  businessName: string
  ordersCount: number
  /** 4 compact stats for 2×2 grid: Jualan, Pesanan, Komisen, Website */
  stats: [MobileStat, MobileStat, MobileStat, MobileStat]
  /** 3 action cards */
  actions: MobileActionItem[]
  websites: WebsiteItem[]
  activityEvents: ActivityEvent[]
  /** Website card state */
  deleteConfirmId: string | null
  deletingId: string | null
  /** Callbacks */
  onCreateNew: () => void
  onView: (website: WebsiteItem) => void
  onEdit: (website: WebsiteItem) => void
  onDelete: (websiteId: string) => void
  onDeleteConfirm: (websiteId: string) => void
  onDeleteCancel: () => void
  onUpgradeClick: () => void
  onRenewClick: () => void
  /** Logout handler (calls supabase.auth.signOut) */
  onLogout?: () => void
}

export default function MobileDashboard({
  userName,
  businessName,
  ordersCount,
  stats,
  actions,
  websites,
  activityEvents,
  deleteConfirmId,
  deletingId,
  onCreateNew,
  onView,
  onEdit,
  onDelete,
  onDeleteConfirm,
  onDeleteCancel,
  onUpgradeClick,
  onRenewClick,
  onLogout,
}: MobileDashboardProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="md:hidden">
      {/* ── 2. Slide-in drawer ── */}
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        ordersCount={ordersCount}
        onLogout={onLogout}
      />

      {/* Drawer trigger (floats over header area on far left) */}
      <button
        onClick={() => setDrawerOpen(true)}
        className="fixed top-3 left-3 z-[60] md:hidden flex items-center justify-center w-11 h-11 rounded-xl bg-transparent text-white/60 active:bg-white/[0.08] transition-colors"
        aria-label="Buka menu"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* ── 3. Greeting (compact padding) ── */}
      <div className="px-4 pt-6 pb-1">
        <DashboardGreeting
          userName={userName}
          businessName={businessName}
        />
      </div>

      {/* ── 4. Hero stats 2×2 grid ── */}
      <div className="grid grid-cols-2 gap-2.5 px-4 mt-4 mb-6">
        {stats.map((stat, i) => (
          <CompactStatCard key={i} stat={stat} />
        ))}
      </div>

      {/* ── 5. Action cards stacked ── */}
      <section className="px-4 mb-6">
        <h2 className="font-geist font-semibold text-base text-white tracking-[-0.02em] mb-3">
          Tindakan pantas
        </h2>
        <div className="flex flex-col gap-3">
          {actions.map((action) => (
            <ActionCard
              key={action.title}
              icon={action.icon}
              title={action.title}
              description={action.description}
              meta={action.meta}
              hue={action.hue}
              href={action.href}
              featured={action.featured}
            />
          ))}
        </div>
      </section>

      {/* ── 6. Websites — 1 column stacked ── */}
      <section className="px-4 mb-6">
        <div className="flex justify-between items-center mb-3">
          <h2 className="font-geist font-semibold text-base text-white tracking-[-0.02em] m-0">
            Website Saya
          </h2>
          <span className="font-geist-mono text-[10px] text-[#4A4A5C] tracking-[0.08em] uppercase">
            {websites.length} website
          </span>
        </div>
        <div className="flex flex-col gap-3">
          {websites.map((site) => (
            <WebsiteCard
              key={site.id}
              name={site.name}
              subdomain={site.subdomain}
              status={site.status}
              templateImage={site.templateImage}
              orders={site.orders}
              views={site.views}
              isDeleteConfirm={deleteConfirmId === site.id}
              isDeleting={deletingId === site.id}
              onView={() => onView(site)}
              onEdit={() => onEdit(site)}
              onDelete={() => onDelete(site.id)}
              onDeleteConfirm={() => onDeleteConfirm(site.id)}
              onDeleteCancel={onDeleteCancel}
            />
          ))}
        </div>
      </section>

      {/* ── 7. Activity feed — full width ── */}
      <section className="px-4 mb-6">
        <h2 className="font-geist font-semibold text-base text-white tracking-[-0.02em] mb-3">
          Aktiviti terkini
        </h2>
        <ActivityFeed events={activityEvents} />
      </section>

      {/* ── 8. Inline usage widget ── */}
      <section className="px-4 mb-24">
        <div
          className="rounded-2xl overflow-hidden"
          style={{
            background: '#161623',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <UsageWidget
            onUpgradeClick={onUpgradeClick}
            onRenewClick={onRenewClick}
            compact
          />
        </div>
      </section>

      {/* ── 9. FAB — "+ Bina Website Baru" ── */}
      <button
        onClick={onCreateNew}
        className="fixed bottom-6 right-4 z-40 md:hidden flex items-center gap-2 rounded-2xl py-3.5 px-5 font-geist font-bold text-sm text-[#0B0B15] transition-transform active:scale-95"
        style={{
          background: 'linear-gradient(135deg, #C7FF3D, #A8E81C)',
          boxShadow:
            '0 0 0 1px rgba(199,255,61,0.4), 0 8px 24px rgba(199,255,61,0.35), 0 2px 8px rgba(0,0,0,0.3)',
        }}
      >
        <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 5v14M5 12h14" />
        </svg>
        Bina Website Baru
      </button>
    </div>
  )
}

/* ── Compact stat card for 2×2 mobile grid ── */

function CompactStatCard({ stat }: { stat: MobileStat }) {
  const isFeatured = stat.featured

  return (
    <div
      className={`
        rounded-2xl p-4 relative overflow-hidden
        ${isFeatured
          ? 'bg-gradient-to-b from-[#0F0F1F] to-[#120D55] border border-[rgba(199,255,61,0.18)]'
          : 'bg-[#161623] border border-white/[0.07]'
        }
      `}
    >
      {/* Featured glow */}
      {isFeatured && (
        <div
          className="absolute -top-6 -right-6 w-24 h-24 rounded-full pointer-events-none"
          style={{
            background: 'radial-gradient(circle, rgba(199,255,61,0.15), transparent 70%)',
          }}
        />
      )}

      {/* Label */}
      <div className="dash-eyebrow text-[9px] mb-2 relative flex items-center gap-1">
        {stat.pulse && <PulseDot />}
        <span style={isFeatured ? { color: '#C7FF3D', fontWeight: 600 } : undefined}>
          {stat.label}
        </span>
      </div>

      {/* Value */}
      <div
        className="font-geist font-bold text-2xl tracking-[-0.04em] dash-tnum leading-none mb-1.5 relative"
        style={{
          color: isFeatured ? '#C7FF3D' : '#fff',
          textShadow: isFeatured ? '0 0 30px rgba(199,255,61,0.3)' : undefined,
        }}
      >
        {stat.value}
      </div>

      {/* Delta */}
      {stat.delta && (
        <div className="relative">
          <span
            className="inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-geist-mono text-[10px] font-semibold"
            style={{
              background: `${stat.delta.color}1F`,
              border: `1px solid ${stat.delta.color}38`,
              color: stat.delta.color,
            }}
          >
            {stat.delta.icon === 'up' && <DeltaArrow direction="up" />}
            {stat.delta.icon === 'down' && <DeltaArrow direction="down" />}
            {stat.delta.text}
          </span>
        </div>
      )}
    </div>
  )
}

/* ── Slide-in drawer ── */

function MobileDrawer({
  open,
  onClose,
  ordersCount,
  onLogout,
}: {
  open: boolean
  onClose: () => void
  ordersCount: number
  onLogout?: () => void
}) {
  return (
    <>
      {/* Backdrop */}
      <div
        className={`
          fixed inset-0 z-[70] bg-black/60 transition-opacity duration-300
          ${open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}
        `}
        onClick={onClose}
      />

      {/* Drawer panel */}
      <nav
        className={`
          fixed top-0 left-0 bottom-0 z-[80] w-72 bg-[#0B0B15] border-r border-white/[0.08]
          flex flex-col transition-transform duration-300 ease-[cubic-bezier(.25,1,.5,1)]
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/[0.06] shrink-0">
          <div className="flex items-center gap-2">
            <img src="/brand/logo-mark.svg" alt="BinaApp" className="h-6 w-6" />
            <span className="text-sm font-semibold text-white tracking-tight">binaapp</span>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-lg grid place-items-center text-white/40 hover:text-white hover:bg-white/[0.06] transition-colors"
            aria-label="Tutup menu"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Nav links */}
        <div className="flex-1 overflow-y-auto py-3 px-3">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={`
                flex items-center justify-between rounded-xl px-4 py-3 text-sm font-medium transition-colors min-h-[44px]
                ${item.active
                  ? 'text-white bg-white/[0.07]'
                  : 'text-white/50 hover:text-white hover:bg-white/[0.04]'
                }
              `}
            >
              {item.label}
              {item.hasBadge && ordersCount > 0 && (
                <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#C7FF3D] px-1.5 text-[11px] font-bold text-[#0B0B15]">
                  {ordersCount}
                </span>
              )}
            </a>
          ))}

          {/* Divider */}
          <div className="my-3 mx-4 border-t border-white/[0.06]" />

          {/* Account links */}
          {ACCOUNT_ITEMS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              onClick={onClose}
              className="flex items-center rounded-xl px-4 py-3 text-sm text-white/40 hover:text-white hover:bg-white/[0.04] transition-colors min-h-[44px]"
            >
              {item.label}
            </a>
          ))}
          <button
            onClick={() => { onClose(); onLogout?.() }}
            className="flex items-center rounded-xl px-4 py-3 text-sm text-white/40 hover:text-white hover:bg-white/[0.04] transition-colors min-h-[44px] w-full bg-transparent border-0 cursor-pointer"
          >
            Log Keluar
          </button>
        </div>
      </nav>
    </>
  )
}

/* ── Tiny internal atoms ── */

function PulseDot() {
  return (
    <span className="relative inline-block w-1.5 h-1.5">
      <span className="absolute inset-0 rounded-full bg-[#FF5A5F] animate-pulse-red" />
      <span className="absolute inset-0 rounded-full bg-[#FF5A5F]" />
    </span>
  )
}

function DeltaArrow({ direction }: { direction: 'up' | 'down' }) {
  return (
    <svg width={9} height={9} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
      {direction === 'up' ? (
        <path d="M7 17 17 7M7 7h10v10" />
      ) : (
        <path d="M17 7 7 17M17 17H7V7" />
      )}
    </svg>
  )
}

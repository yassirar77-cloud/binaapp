'use client'

/**
 * Tempahan — the merchant's side of the booking engine.
 *
 * Three tabs: the bookings themselves, the services customers can book,
 * and opening hours / slot rules. Everything goes through the backend
 * booking API (/api/v1/bookings/admin/*); the browser never reads the
 * booking tables directly.
 */

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

import DashboardHeader from '@/components/dashboard-new/DashboardHeader'
import { getCurrentUser, getStoredToken, signOut, supabase } from '@/lib/supabase'

import BookingsTab from './components/BookingsTab'
import ServicesTab from './components/ServicesTab'
import SettingsTab from './components/SettingsTab'
import { Button, Notice } from './components/ui'

import '@/components/dashboard-new/dashboard.css'

interface WebsiteOption {
  id: string
  label: string
}

type Tab = 'bookings' | 'services' | 'settings'

const TABS: Array<{ key: Tab; label: string }> = [
  { key: 'bookings', label: 'Tempahan' },
  { key: 'services', label: 'Servis' },
  { key: 'settings', label: 'Waktu & Tetapan' },
]

export default function TempahanClient() {
  const router = useRouter()
  const [userName, setUserName] = useState('Pengguna')
  const [websites, setWebsites] = useState<WebsiteOption[]>([])
  const [websiteId, setWebsiteId] = useState('')
  const [tab, setTab] = useState<Tab>('bookings')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const load = async () => {
      const token = getStoredToken()
      const user = await getCurrentUser()
      if (!token || !user) {
        router.push('/login')
        return
      }
      setUserName((user as any).user_metadata?.full_name || user.email || 'Pengguna')
      if (!supabase) {
        setError('Ralat sambungan. Sila cuba lagi.')
        setLoading(false)
        return
      }
      const { data: rows, error: sbError } = await supabase
        .from('websites')
        .select('id, business_name, subdomain')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })
      if (sbError) {
        setError('Gagal memuatkan senarai website.')
        setLoading(false)
        return
      }
      const options = (rows || []).map((w: any) => ({
        id: w.id,
        label: w.business_name || w.subdomain || 'Website',
      }))
      setWebsites(options)
      const requested =
        typeof window !== 'undefined'
          ? new URLSearchParams(window.location.search).get('website')
          : null
      setWebsiteId(options.find((o) => o.id === requested)?.id || options[0]?.id || '')
      setLoading(false)
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const bookingUrl =
    websiteId && typeof window !== 'undefined' ? `${window.location.origin}/tempah/${websiteId}` : ''

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(bookingUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      window.prompt('Salin pautan tempahan:', bookingUrl)
    }
  }

  return (
    <div className="dash-bg min-h-screen font-geist">
      <div className="dash-dotgrid" />
      <div className="dash-glow-top" />
      <DashboardHeader userName={userName} onLogout={() => signOut()} />

      <main className="relative mx-auto max-w-5xl px-4 lg:px-6 py-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-white tracking-tight">Tempahan</h1>
            <p className="text-[13px] text-white/40 mt-0.5">
              Slot temujanji untuk pelanggan — servis, waktu operasi dan senarai tempahan
            </p>
          </div>
          {websites.length > 1 && (
            <select
              aria-label="Pilih website"
              value={websiteId}
              onChange={(e) => setWebsiteId(e.target.value)}
              className="rounded-full bg-white/[0.05] border border-white/[0.08] px-3.5 py-1.5 text-xs text-white/80 focus:outline-none focus:border-[#C7FF3D]/50"
            >
              {websites.map((w) => (
                <option key={w.id} value={w.id} className="bg-[#161623]">
                  {w.label}
                </option>
              ))}
            </select>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-32">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
          </div>
        ) : error ? (
          <Notice tone="error">{error}</Notice>
        ) : !websiteId ? (
          <div className="dash-surface p-10 text-center">
            <p className="text-white font-medium">Anda belum mempunyai website</p>
            <p className="text-[13px] text-white/40 mt-1">
              Bina website dahulu, kemudian buka tempahan slot untuk pelanggan anda.
            </p>
          </div>
        ) : (
          <>
            <div className="dash-surface p-4 flex flex-wrap items-center gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-[11px] uppercase tracking-wider text-white/40">Pautan tempahan pelanggan</p>
                <p className="text-sm text-white/80 truncate">{bookingUrl}</p>
              </div>
              <Button onClick={copyLink}>{copied ? 'Disalin ✓' : 'Salin pautan'}</Button>
              <a
                href={bookingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full px-4 py-2 text-xs font-semibold bg-white/[0.06] text-white/80 border border-white/[0.08] hover:bg-white/[0.1]"
              >
                Buka
              </a>
            </div>

            <div role="tablist" className="flex gap-1 rounded-full bg-white/[0.04] border border-white/[0.06] p-1 w-fit">
              {TABS.map((t) => (
                <button
                  key={t.key}
                  role="tab"
                  aria-selected={tab === t.key}
                  onClick={() => setTab(t.key)}
                  className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                    tab === t.key ? 'bg-[#C7FF3D] text-black' : 'text-white/60 hover:text-white'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* key = remount on website switch so no tab shows the previous site's data */}
            {tab === 'bookings' && <BookingsTab key={websiteId} websiteId={websiteId} />}
            {tab === 'services' && <ServicesTab key={websiteId} websiteId={websiteId} />}
            {tab === 'settings' && <SettingsTab key={websiteId} websiteId={websiteId} />}
          </>
        )}
      </main>
    </div>
  )
}

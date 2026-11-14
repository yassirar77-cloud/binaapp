'use client'

/**
 * Promosi — the merchant's side of voucher codes and loyalty points.
 *
 * Two tabs: voucher codes customers type at checkout, and the points
 * programme. Everything goes through /api/v1/promotions/*; discounts are
 * always priced by the backend when the order is placed.
 */

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

import DashboardHeader from '@/components/dashboard-new/DashboardHeader'
import { getCurrentUser, getStoredToken, signOut, supabase } from '@/lib/supabase'

import { Notice } from '../tempahan/components/ui'
import LoyaltyTab from './components/LoyaltyTab'
import VouchersTab from './components/VouchersTab'

import '@/components/dashboard-new/dashboard.css'

interface WebsiteOption {
  id: string
  label: string
}

type Tab = 'vouchers' | 'loyalty'

const TABS: Array<{ key: Tab; label: string }> = [
  { key: 'vouchers', label: 'Baucar' },
  { key: 'loyalty', label: 'Mata Ganjaran' },
]

export default function PromosiClient() {
  const router = useRouter()
  const [userName, setUserName] = useState('Pengguna')
  const [websites, setWebsites] = useState<WebsiteOption[]>([])
  const [websiteId, setWebsiteId] = useState('')
  const [tab, setTab] = useState<Tab>('vouchers')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  return (
    <div className="dash-bg min-h-screen font-geist">
      <div className="dash-dotgrid" />
      <div className="dash-glow-top" />
      <DashboardHeader userName={userName} onLogout={() => signOut()} />

      <main className="relative mx-auto max-w-5xl px-4 lg:px-6 py-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-white tracking-tight">Promosi</h1>
            <p className="text-[13px] text-white/40 mt-0.5">
              Kod baucar dan mata ganjaran untuk pesanan pelanggan anda
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
              Bina website dahulu, kemudian tawarkan baucar dan mata ganjaran kepada pelanggan anda.
            </p>
          </div>
        ) : (
          <>
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
            {tab === 'vouchers' && <VouchersTab key={websiteId} websiteId={websiteId} />}
            {tab === 'loyalty' && <LoyaltyTab key={websiteId} websiteId={websiteId} />}
          </>
        )}
      </main>
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { getStoredToken, getCurrentUser, getApiAuthToken } from '@/lib/supabase'
import DashboardHeader from '@/components/dashboard-new/DashboardHeader'
import DashboardFooter from '@/components/dashboard-new/DashboardFooter'
import '@/components/dashboard-new/dashboard.css'

const OwnerChatDashboard = dynamic(
  () => import('@/components/OwnerChatDashboard'),
  { ssr: false },
)

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface Website {
  id: string
  name?: string
  business_name?: string
  subdomain?: string
}

export default function ChatPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [websites, setWebsites] = useState<Website[]>([])
  const [ownerName, setOwnerName] = useState('Pemilik Kedai')
  const [userName, setUserName] = useState('Pengguna')
  const [chatEnabled, setChatEnabled] = useState(true)
  const [chatChecking, setChatChecking] = useState(true)

  useEffect(() => {
    init()
  }, [])

  async function init() {
    const token = getStoredToken()
    const user = await getCurrentUser()

    if (!token || !user) {
      router.push('/login')
      return
    }

    const displayName =
      (user as any).user_metadata?.full_name ||
      (user as any).email?.split('@')[0] ||
      'Pengguna'
    setUserName(displayName)

    // Load websites
    const sites = await fetchWebsites(token)
    setWebsites(sites)

    // Derive owner name from first website's business_name or user name
    const businessName = sites[0]?.business_name || sites[0]?.name
    setOwnerName(businessName || displayName || 'Pemilik Kedai')

    // Check chat API health
    await checkChatApi()

    setLoading(false)
  }

  async function fetchWebsites(token: string): Promise<Website[]> {
    try {
      const res = await fetch(`${API_BASE}/api/v1/websites/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (!res.ok) return []
      const data = await res.json()
      return (data || []).map((w: any) => ({
        ...w,
        name: w.business_name,
      }))
    } catch {
      return []
    }
  }

  async function checkChatApi() {
    try {
      setChatChecking(true)
      const token = await getApiAuthToken()
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`

      const res = await fetch(`${API_BASE}/api/v1/chat/conversations`, { headers })
      setChatEnabled(res.ok)
    } catch {
      setChatEnabled(false)
    } finally {
      setChatChecking(false)
    }
  }

  function handleLogout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('binaapp_token')
      localStorage.removeItem('binaapp_user')
    }
    router.push('/')
  }

  // ── Render ─────────────────────────────────────────────

  if (loading) {
    return (
      <div className="dash-bg min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#C7FF3D] mx-auto" />
          <p className="text-white/40 mt-4 text-sm">Memuatkan chat...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dash-bg min-h-screen relative">
      <div className="dash-dotgrid" />
      <div className="dash-glow-top" />
      <div className="dash-glow-accent" />

      <DashboardHeader userName={userName} onLogout={handleLogout} />

      <main className="relative z-10 mx-auto max-w-6xl px-4 lg:px-6 py-8">
        {/* Page header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-white">Chat Pelanggan</h1>
          <p className="text-sm text-white/40 mt-1">
            Urus mesej pelanggan dari semua website anda
          </p>
        </div>

        {/* Chat API checking */}
        {chatChecking && (
          <div className="mb-6 p-4 rounded-2xl border border-white/[0.08] bg-white/[0.03]">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#C7FF3D]" />
              <span className="text-white/50 text-sm">Menyemak sistem chat...</span>
            </div>
          </div>
        )}

        {/* Chat API error */}
        {!chatEnabled && !chatChecking && (
          <div className="mb-6 p-4 rounded-2xl border border-red-500/20 bg-red-500/10">
            <div className="flex items-start gap-3">
              <span className="text-2xl">&#9888;</span>
              <div className="flex-1">
                <h3 className="font-bold text-red-400 mb-1">Chat Tidak Dapat Dihubungi</h3>
                <p className="text-sm text-red-400/70 mb-2">
                  Sistem chat tidak dapat dihubungi. Sila cuba semula atau hubungi sokongan.
                </p>
                <button
                  onClick={() => checkChatApi()}
                  className="text-sm bg-red-500/20 hover:bg-red-500/30 text-red-400 px-3 py-1 rounded-lg transition-colors"
                >
                  Cuba Semula
                </button>
              </div>
            </div>
          </div>
        )}

        {/* No websites */}
        {websites.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">&#128172;</div>
            <p className="text-white/50 text-sm mb-4">
              Tiada website. Bina website dahulu untuk mula chat dengan pelanggan.
            </p>
            <Link
              href="/create"
              className="inline-block px-6 py-3 rounded-xl bg-[#C7FF3D] text-[#0B0B15] font-medium text-sm hover:bg-[#DDFF7A] transition-colors"
            >
              Bina Website Sekarang
            </Link>
          </div>
        ) : chatEnabled ? (
          <OwnerChatDashboard
            websites={websites}
            ownerName={ownerName}
          />
        ) : null}
      </main>

      <div className="relative z-10 mx-auto max-w-6xl px-4 lg:px-6 pb-8">
        <DashboardFooter />
      </div>
    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'

const OwnerChatDashboard = dynamic(() => import('@/components/OwnerChatDashboard'), { ssr: false })

interface Website {
  id: string
  business_name?: string
  name?: string
  subdomain?: string
}

export default function ChatDashboardPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [websites, setWebsites] = useState<Website[]>([])
  const [ownerName, setOwnerName] = useState('')

  useEffect(() => {
    loadChatData()
  }, [])

  const loadChatData = async () => {
    if (!supabase) {
      setError('Supabase tidak tersedia')
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.user) {
        router.push('/login')
        return
      }

      setUser(session.user)

      const { data: profileData } = await supabase
        .from('profiles')
        .select('full_name, business_name')
        .eq('id', session.user.id)
        .maybeSingle()

      if (profileData) {
        setOwnerName(profileData.business_name || profileData.full_name || '')
      }

      const { data: websitesData, error: websitesError } = await supabase
        .from('websites')
        .select('id, business_name, name, subdomain')
        .eq('user_id', session.user.id)
        .order('created_at', { ascending: false })

      if (websitesError) {
        throw websitesError
      }

      setWebsites(websitesData || [])
    } catch (err) {
      console.error('[ChatDashboard] Failed to load data:', err)
      setError('Gagal memuatkan data chat')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Memuatkan chat...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-gray-800 mb-2">Sila log masuk semula</h1>
          <Link href="/login" className="text-orange-600 hover:text-orange-700 font-medium">
            Log masuk
          </Link>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">Ralat Memuatkan Chat</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={loadChatData}
            className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Cuba Lagi
          </button>
        </div>
      </div>
    )
  }

  if (websites.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
          <div className="text-6xl mb-4">🌐</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">Tiada Laman Web</h2>
          <p className="text-gray-600 mb-6">
            Sila bina website dahulu untuk mula menerima mesej pelanggan.
          </p>
          <Link
            href="/create"
            className="inline-block bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Bina Website
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-gray-600 hover:text-gray-900">
              ← Dashboard
            </Link>
            <span className="text-xl font-bold text-gray-900">Chat Pelanggan</span>
          </div>
          <Link href="/profile" className="text-sm text-gray-600 hover:text-gray-900">
            Profil
          </Link>
        </nav>
      </header>

      <div className="container mx-auto px-4 py-6 md:py-10">
        <div className="bg-white rounded-2xl shadow-lg p-4 md:p-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-6">
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900">💬 Chat Pelanggan</h1>
              <p className="text-gray-600 text-sm md:text-base">
                Urus mesej pelanggan dari semua website anda dalam satu tempat.
              </p>
            </div>
            <Link
              href="/my-projects"
              className="text-sm text-orange-600 hover:text-orange-700 font-medium"
            >
              Lihat website saya
            </Link>
          </div>

          <OwnerChatDashboard
            websites={websites}
            ownerName={ownerName || 'Pemilik Kedai'}
          />
        </div>
      </div>
    </div>
  )
}

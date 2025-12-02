/**
 * Dashboard Page - Main app interface
 */

'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getCurrentUser, signOut } from '@/lib/supabase'
import { apiClient, Website } from '@/lib/api'
import toast from 'react-hot-toast'
import { Plus, Globe, LogOut, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { getWebsiteStatus } from '@/lib/utils'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [websites, setWebsites] = useState<Website[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuth()
    loadWebsites()
  }, [])

  const checkAuth = async () => {
    const currentUser = await getCurrentUser()
    if (!currentUser) {
      router.push('/login')
      return
    }
    setUser(currentUser)
  }

  const loadWebsites = async () => {
    try {
      const response = await apiClient.getWebsites()
      setWebsites(response.data)
    } catch (error) {
      toast.error('Gagal memuatkan websites')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await signOut()
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="btn btn-secondary flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Log Keluar
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Website Saya</h1>
            <p className="text-gray-600">
              Anda mempunyai {websites.length} website
            </p>
          </div>
          <Link href="/dashboard/create" className="btn btn-primary flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Cipta Website Baharu
          </Link>
        </div>

        {/* Websites Grid */}
        {websites.length === 0 ? (
          <div className="text-center py-16">
            <Globe className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Tiada website lagi</h3>
            <p className="text-gray-600 mb-6">
              Mula cipta website pertama anda dengan AI
            </p>
            <Link href="/dashboard/create" className="btn btn-primary">
              Cipta Website Sekarang
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {websites.map((website) => (
              <WebsiteCard key={website.id} website={website} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function WebsiteCard({ website }: { website: Website }) {
  const status = getWebsiteStatus(website.status)

  return (
    <div className="card hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-bold text-lg mb-1">{website.business_name}</h3>
          <p className="text-sm text-gray-600">{website.subdomain}.binaapp.my</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full ${status.color}`}>
          {status.label}
        </span>
      </div>

      <div className="text-sm text-gray-600 mb-4">
        Dicipta: {new Date(website.created_at).toLocaleDateString('ms-MY')}
      </div>

      <div className="flex gap-2">
        {website.status === 'published' && (
          <a
            href={website.full_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary flex-1 text-sm"
          >
            Lihat Website
          </a>
        )}
        <Link
          href={`/dashboard/website/${website.id}`}
          className="btn btn-outline flex-1 text-sm"
        >
          {website.status === 'draft' ? 'Terbitkan' : 'Urus'}
        </Link>
      </div>
    </div>
  )
}

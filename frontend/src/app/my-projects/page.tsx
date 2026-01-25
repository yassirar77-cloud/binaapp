'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getCurrentUser, getStoredToken, signOut } from '@/lib/supabase'

// Backend API URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface Website {
  id: string
  business_name: string
  subdomain: string | null
  full_url: string | null
  status: string
  created_at: string
  published_at: string | null
}

interface User {
  id: string
  email: string
  full_name?: string
}

export default function MyProjectsPage() {
  const router = useRouter()

  const [loading, setLoading] = useState(true)
  const [websites, setWebsites] = useState<Website[]>([])
  const [user, setUser] = useState<User | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  useEffect(() => {
    checkAuthAndGetWebsites()
  }, [])

  async function checkAuthAndGetWebsites() {
    try {
      setLoading(true)

      // Check for custom BinaApp auth token
      const token = getStoredToken()
      const currentUser = await getCurrentUser()

      if (!token || !currentUser) {
        router.push('/login')
        return
      }

      setUser(currentUser as User)

      // Fetch websites from backend API
      const response = await fetch(`${API_BASE}/api/v1/websites/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.status === 401) {
        // Token expired or invalid
        router.push('/login')
        return
      }

      if (response.ok) {
        const data = await response.json()
        setWebsites(data || [])
      } else {
        console.error('Error fetching websites:', response.status)
        setWebsites([])
      }
    } catch (error) {
      console.error('Error:', error)
      setWebsites([])
    } finally {
      setLoading(false)
    }
  }

  async function deleteWebsite(id: string, websiteName: string) {
    // Enhanced confirmation dialog
    const confirmed = confirm(
      `Adakah anda pasti mahu memadam "${websiteName}"?\n\n` +
      `Ini akan memadam:\n` +
      `• Website dan semua kandungan\n` +
      `• Semua menu items\n` +
      `• Semua pesanan\n` +
      `• Semua data berkaitan\n\n` +
      `Tindakan ini TIDAK BOLEH dibatalkan!`
    )

    if (!confirmed) return

    try {
      setDeleting(id)

      // Get auth token
      const token = getStoredToken()
      if (!token) {
        alert('Sila log masuk semula')
        router.push('/login')
        return
      }

      // Call backend API endpoint
      const response = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const result = await response.json()
      console.log('Delete success:', result)

      // Remove from local state
      setWebsites(websites.filter((w) => w.id !== id))

      // Show success message
      alert(`✅ Website "${websiteName}" berjaya dipadam!`)

    } catch (error) {
      console.error('Error deleting website:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      alert(`❌ Ralat memadam website:\n${errorMessage}\n\nSila cuba lagi atau hubungi sokongan.`)
    } finally {
      setDeleting(null)
    }
  }

  async function handleLogout() {
    await signOut()
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">Sila Log Masuk</h1>
          <Link href="/login" className="text-blue-500 hover:underline">
            Log Masuk
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/profile" className="text-sm text-gray-600 hover:text-gray-900">
              Profil
            </Link>
            <Link href="/create" className="text-sm text-gray-600 hover:text-gray-900">
              Bina Website
            </Link>
            <Link href="/dashboard/billing" className="text-sm text-gray-600 hover:text-gray-900">
              💎 Langganan
            </Link>
            <button
              onClick={handleLogout}
              className="text-sm text-red-500 hover:text-red-600"
            >
              Log Keluar
            </button>
          </div>
        </nav>
      </header>

      <div className="py-12">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Website Saya</h1>
              <p className="text-gray-500 mt-1">
                {websites.length} website dijumpai
              </p>
            </div>
            <Link
              href="/create"
              className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors flex items-center gap-2"
            >
              <span>+</span> Bina Website Baru
            </Link>
          </div>

          {websites.length === 0 ? (
            <div className="bg-white rounded-xl shadow-lg p-12 text-center">
              <span className="text-6xl mb-4 block">🌐</span>
              <h2 className="text-xl font-semibold text-gray-700 mb-2">
                Tiada website lagi
              </h2>
              <p className="text-gray-500 mb-6">
                Mula bina website pertama anda dengan AI sekarang!
              </p>
              <Link
                href="/create"
                className="inline-block bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-8 rounded-lg transition-colors"
              >
                ✨ Bina Website Sekarang
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {websites.map((website) => (
                <div
                  key={website.id}
                  className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 group"
                >
                  {/* Website Preview */}
                  <div className="h-48 bg-gradient-to-br from-blue-400 to-purple-500 relative overflow-hidden">
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-white text-5xl group-hover:scale-110 transition-transform">
                        🌐
                      </span>
                    </div>
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors"></div>
                    <div className="absolute top-3 right-3">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          website.status === 'published'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {website.status === 'published' ? '🟢 Live' : '📝 Draf'}
                      </span>
                    </div>
                  </div>

                  {/* Website Info */}
                  <div className="p-5">
                    <h3 className="font-semibold text-gray-800 text-lg mb-1 truncate">
                      {website.business_name}
                    </h3>
                    {website.subdomain && (
                      <a
                        href={website.full_url || `https://${website.subdomain}.binaapp.my`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 text-sm mb-3 block hover:underline"
                      >
                        {website.subdomain}.binaapp.my ↗
                      </a>
                    )}
                    <p className="text-gray-400 text-xs mb-4">
                      Dibuat: {new Date(website.created_at).toLocaleDateString('ms-MY', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      })}
                    </p>

                    {/* Actions */}
                    <div className="flex flex-col gap-2">
                      <div className="flex gap-2">
                        {(website.full_url || website.status === 'published') && (
                          <a
                            href={website.full_url || `https://${website.subdomain}.binaapp.my`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 bg-green-500 hover:bg-green-600 text-white text-center py-2 rounded-lg text-sm font-medium transition-colors"
                          >
                            👁 Lihat Live
                          </a>
                        )}
                        <Link
                          href={`/editor/${website.id}`}
                          className="flex-1 bg-blue-500 hover:bg-blue-600 text-white text-center py-2 rounded-lg text-sm font-medium transition-colors"
                        >
                          ✏️ Edit
                        </Link>
                        <button
                          onClick={() => deleteWebsite(website.id, website.business_name)}
                          disabled={deleting === website.id}
                          className="bg-red-100 hover:bg-red-200 text-red-600 px-3 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                        >
                          {deleting === website.id ? '...' : '🗑️'}
                        </button>
                      </div>
                      <Link
                        href={`/analytics/${website.id}`}
                        className="w-full bg-purple-100 hover:bg-purple-200 text-purple-700 text-center py-2 rounded-lg text-sm font-medium transition-colors"
                      >
                        📊 Analytics
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Stats Footer */}
          {websites.length > 0 && (
            <div className="mt-8 bg-white rounded-xl shadow-lg p-6">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-3xl font-bold text-blue-500">{websites.length}</div>
                  <div className="text-gray-500 text-sm">Jumlah Website</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-green-500">
                    {websites.filter((w) => w.status === 'published').length}
                  </div>
                  <div className="text-gray-500 text-sm">Website Live</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-yellow-500">
                    {websites.filter((w) => w.status !== 'published').length}
                  </div>
                  <div className="text-gray-500 text-sm">Draf</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

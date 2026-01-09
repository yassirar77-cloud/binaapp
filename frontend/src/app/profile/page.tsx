'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'

export default function ProfilePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState({ full_name: '', business_name: '', phone: '' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [websites, setWebsites] = useState<any[]>([])

  useEffect(() => {
    loadUserData()
  }, [])

  async function loadUserData() {
    if (!supabase) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)

      // EXACT SAME METHOD AS MY-PROJECTS PAGE
      const { data: { user } } = await supabase.auth.getUser()

      if (!user) {
        router.push('/login')
        return
      }

      setUser(user)

      // Load profile
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user.id)
        .maybeSingle()

      if (profileData) {
        setProfile({
          full_name: profileData.full_name || '',
          business_name: profileData.business_name || '',
          phone: profileData.phone || ''
        })
      }

      // Load websites
      const { data: websitesData } = await supabase
        .from('websites')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })

      setWebsites(websitesData || [])
    } catch (error) {
      console.error('Error loading user data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase || !user) return

    setSaving(true)
    try {
      await supabase.from('profiles').upsert({
        id: user.id,
        email: user.email,
        ...profile,
        updated_at: new Date().toISOString()
      })
      setMsg('✅ Disimpan!')
      setTimeout(() => setMsg(''), 3000)
    } catch (error) {
      console.error('Error saving profile:', error)
      setMsg('❌ Gagal simpan')
    } finally {
      setSaving(false)
    }
  }

  async function handleLogout() {
    if (!supabase) return
    await supabase.auth.signOut()
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
      {/* Header - SAME AS MY-PROJECTS */}
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/my-projects" className="text-sm text-gray-600 hover:text-gray-900">
              Website Saya
            </Link>
            <Link href="/create" className="text-sm text-gray-600 hover:text-gray-900">
              Bina Website
            </Link>
            <button onClick={handleLogout} className="text-sm text-red-500 hover:text-red-600">
              Log Keluar
            </button>
          </div>
        </nav>
      </header>

      <div className="py-12">
        <div className="max-w-4xl mx-auto px-4">
          {/* Profile Section */}
          <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
            <h1 className="text-3xl font-bold mb-6">👤 Profil Saya</h1>
            {msg && (
              <div className={`p-4 rounded-lg mb-6 ${msg.includes('✅') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {msg}
              </div>
            )}
            <form onSubmit={saveProfile} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input type="email" value={user.email || ''} disabled className="w-full p-3 bg-gray-100 rounded-lg border" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nama Penuh</label>
                <input
                  type="text"
                  value={profile.full_name}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  placeholder="Nama anda"
                  className="w-full p-3 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nama Perniagaan</label>
                <input
                  type="text"
                  value={profile.business_name}
                  onChange={(e) => setProfile({ ...profile, business_name: e.target.value })}
                  placeholder="Nama perniagaan"
                  className="w-full p-3 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nombor Telefon</label>
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  placeholder="01X-XXX XXXX"
                  className="w-full p-3 border rounded-lg"
                />
              </div>
              <button type="submit" disabled={saving} className="w-full py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium disabled:opacity-50">
                {saving ? 'Menyimpan...' : '💾 Simpan Profil'}
              </button>
            </form>
          </div>

          {/* Websites Section */}
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">🌐 Website Saya ({websites.length})</h2>
              <Link href="/create" className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 text-sm font-medium">
                + Bina Website Baru
              </Link>
            </div>

            {websites.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🌐</div>
                <p className="text-gray-500 mb-6">Tiada website lagi</p>
                <Link href="/create" className="inline-block bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600">
                  ✨ Bina Website Sekarang
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {websites.map((site) => (
                  <div key={site.id} className="border rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg">{site.name}</h3>
                        {site.subdomain && (
                          <a href={`https://${site.subdomain}.binaapp.my`} target="_blank" className="text-blue-500 hover:underline text-sm">
                            {site.subdomain}.binaapp.my ↗
                          </a>
                        )}
                        <p className="text-xs text-gray-500 mt-1">Dibuat: {new Date(site.created_at).toLocaleDateString('ms-MY')}</p>
                      </div>
                      <div className="flex gap-2">
                        {site.published_url && (
                          <a href={site.published_url} target="_blank" className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 text-sm">
                            👁 Lihat
                          </a>
                        )}
                        <Link href={`/editor/${site.id}`} className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 text-sm">
                          ✏️ Edit
                        </Link>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

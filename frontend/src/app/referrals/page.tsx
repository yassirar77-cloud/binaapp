'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface ReferralStats {
  code: string | null
  total_referrals: number
  total_credits_earned: number
  is_active: boolean
  referrals: Array<{
    id: string
    referrer_credit: number
    status: string
    created_at: string
  }>
}

export default function ReferralsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<ReferralStats | null>(null)
  const [applyCode, setApplyCode] = useState('')
  const [applyLoading, setApplyLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const token = getStoredToken()
      if (!token) { router.push('/auth/login'); return }

      const response = await fetch(`${API_BASE_URL}/api/v1/referrals/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const d = await response.json()
        setStats(d.data)
      }
    } catch (err) {
      console.error('Error loading referral data:', err)
    } finally {
      setLoading(false)
    }
  }

  const copyCode = () => {
    if (stats?.code) {
      navigator.clipboard.writeText(stats.code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const shareWhatsApp = () => {
    if (stats?.code) {
      const text = `Jom sertai BinaApp! Guna kod rujukan saya ${stats.code} dan dapatkan RM5 BinaCredit percuma! https://binaapp.my`
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank')
    }
  }

  const shareTelegram = () => {
    if (stats?.code) {
      const text = `Jom sertai BinaApp! Guna kod rujukan saya ${stats.code} dan dapatkan RM5 BinaCredit percuma! https://binaapp.my`
      window.open(`https://t.me/share/url?url=https://binaapp.my&text=${encodeURIComponent(text)}`, '_blank')
    }
  }

  const handleApply = async () => {
    if (!applyCode.trim()) return
    setApplyLoading(true)
    setMessage('')

    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/referrals/apply`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: applyCode.trim().toUpperCase() })
      })

      const data = await response.json()
      if (response.ok) {
        setMessage(data.data?.message || 'Kod berjaya digunakan!')
        setApplyCode('')
        loadData()
      } else {
        setMessage(data.detail || 'Kod tidak sah')
      }
    } catch {
      setMessage('Ralat rangkaian')
    } finally {
      setApplyLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <button onClick={() => router.push('/profile')} className="text-blue-600 text-sm mb-2 hover:underline">&larr; Kembali ke Profil</button>
          <h1 className="text-2xl font-bold text-gray-900">Jemput Rakan</h1>
          <p className="text-gray-600 text-sm mt-1">Jemput rakan dan dapatkan RM5 BinaCredit setiap rujukan berjaya!</p>
        </div>

        {/* Referral Code Card */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl shadow-lg p-6 mb-6 text-white">
          <p className="text-blue-100 text-sm mb-2">Kod Rujukan Anda</p>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl font-bold tracking-wider">{stats?.code || '...'}</span>
            <button
              onClick={copyCode}
              className="bg-white/20 hover:bg-white/30 px-3 py-1 rounded text-sm transition-colors"
            >
              {copied ? 'Disalin!' : 'Salin'}
            </button>
          </div>
          <div className="flex gap-3">
            <button
              onClick={shareWhatsApp}
              className="bg-green-500 hover:bg-green-600 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              WhatsApp
            </button>
            <button
              onClick={shareTelegram}
              className="bg-blue-400 hover:bg-blue-500 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Telegram
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-blue-600">{stats?.total_referrals || 0}</p>
            <p className="text-sm text-gray-500">Jumlah Rujukan</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-green-600">RM{(stats?.total_credits_earned || 0).toFixed(2)}</p>
            <p className="text-sm text-gray-500">Kredit Diperoleh</p>
          </div>
        </div>

        {/* Apply Code */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-3">Guna Kod Rujukan</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={applyCode}
              onChange={(e) => setApplyCode(e.target.value.toUpperCase())}
              placeholder="BINA-XXXX-XXXX"
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleApply}
              disabled={applyLoading || !applyCode.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium disabled:opacity-50 transition-colors"
            >
              {applyLoading ? '...' : 'Guna'}
            </button>
          </div>
          {message && (
            <p className={`mt-2 text-sm ${message.includes('berjaya') ? 'text-green-600' : 'text-red-600'}`}>
              {message}
            </p>
          )}
        </div>

        {/* How it works */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-3">Cara Ia Berfungsi</h3>
          <div className="space-y-3">
            <div className="flex gap-3">
              <span className="bg-blue-100 text-blue-600 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm">1</span>
              <p className="text-gray-700">Kongsi kod rujukan anda dengan rakan</p>
            </div>
            <div className="flex gap-3">
              <span className="bg-blue-100 text-blue-600 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm">2</span>
              <p className="text-gray-700">Rakan mendaftar dan masukkan kod anda</p>
            </div>
            <div className="flex gap-3">
              <span className="bg-blue-100 text-blue-600 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm">3</span>
              <p className="text-gray-700">Kedua-dua anda menerima RM5 BinaCredit!</p>
            </div>
          </div>
        </div>

        {/* Referral History */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h3 className="text-lg font-semibold">Sejarah Rujukan</h3>
          </div>
          {(!stats?.referrals || stats.referrals.length === 0) ? (
            <div className="p-8 text-center text-gray-500">
              Belum ada rujukan. Kongsi kod anda sekarang!
            </div>
          ) : (
            <div className="divide-y">
              {stats.referrals.map((ref) => (
                <div key={ref.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Rujukan berjaya</p>
                    <p className="text-xs text-gray-400">
                      {new Date(ref.created_at).toLocaleDateString('ms-MY')}
                    </p>
                  </div>
                  <span className="text-green-600 font-semibold">+RM{ref.referrer_credit?.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface TrustScore {
  score: number
  trust_level: string
  credit_multiplier: number
  successful_orders: number
  subscription_months: number
  referral_count: number
  legitimate_disputes: number
  fraudulent_disputes: number
  rejected_disputes: number
  payment_failures: number
  terms_violations: number
  all_levels: Record<string, { min: number; max: number; multiplier: number }>
  history: Array<{
    id: string
    old_score: number
    new_score: number
    change_reason: string
    change_amount: number
    created_at: string
  }>
}

const levelNames: Record<string, string> = {
  low: 'Rendah',
  new: 'Baharu',
  standard: 'Standard',
  trusted: 'Dipercayai',
  premium: 'Premium'
}

const levelColors: Record<string, string> = {
  low: 'text-red-500',
  new: 'text-gray-500',
  standard: 'text-blue-500',
  trusted: 'text-green-500',
  premium: 'text-yellow-500'
}

const levelBgColors: Record<string, string> = {
  low: 'from-red-500 to-red-600',
  new: 'from-gray-400 to-gray-500',
  standard: 'from-blue-500 to-blue-600',
  trusted: 'from-green-500 to-green-600',
  premium: 'from-yellow-400 to-yellow-500'
}

export default function TrustScorePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<TrustScore | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const token = getStoredToken()
      if (!token) { router.push('/auth/login'); return }

      const response = await fetch(`${API_BASE_URL}/api/v1/trust/my-score`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const d = await response.json()
        setData(d.data)
      }
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const score = data?.score || 0
  const level = data?.trust_level || 'new'
  const multiplier = data?.credit_multiplier || 1.0
  const percentage = (score / 1000) * 100

  // Calculate stroke offset for circular gauge
  const circumference = 2 * Math.PI * 90
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-6">
          <button onClick={() => router.push('/profile')} className="text-blue-600 text-sm mb-2 hover:underline">&larr; Kembali ke Profil</button>
          <h1 className="text-2xl font-bold text-gray-900">Skor Kepercayaan</h1>
          <p className="text-gray-600 text-sm mt-1">Skor anda berdasarkan aktiviti dan tingkah laku dalam BinaApp</p>
        </div>

        {/* Circular Score Gauge */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6 flex flex-col items-center">
          <div className="relative w-52 h-52 mb-4">
            <svg className="transform -rotate-90 w-52 h-52" viewBox="0 0 200 200">
              <circle cx="100" cy="100" r="90" stroke="#E5E7EB" strokeWidth="12" fill="none" />
              <circle
                cx="100" cy="100" r="90"
                stroke={level === 'premium' ? '#F59E0B' : level === 'trusted' ? '#10B981' : level === 'standard' ? '#3B82F6' : level === 'new' ? '#9CA3AF' : '#EF4444'}
                strokeWidth="12"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                className="transition-all duration-1000"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-bold text-gray-900">{score}</span>
              <span className="text-sm text-gray-500">/ 1000</span>
            </div>
          </div>

          {/* Level Badge */}
          <div className={`bg-gradient-to-r ${levelBgColors[level]} text-white px-6 py-2 rounded-full font-semibold text-lg`}>
            {levelNames[level] || level}
          </div>

          <p className="text-gray-600 mt-3">
            Pengganda kredit: <span className="font-bold text-blue-600">{multiplier}x</span>
          </p>
        </div>

        {/* Trust Levels */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Tahap Kepercayaan</h3>
          <div className="space-y-3">
            {data?.all_levels && Object.entries(data.all_levels).map(([lvl, config]) => (
              <div
                key={lvl}
                className={`flex items-center justify-between p-3 rounded-lg ${lvl === level ? 'bg-blue-50 border-2 border-blue-500' : 'bg-gray-50'}`}
              >
                <div className="flex items-center gap-3">
                  {lvl === level && <span className="w-3 h-3 bg-blue-500 rounded-full"></span>}
                  <div>
                    <p className={`font-medium ${levelColors[lvl]}`}>{levelNames[lvl] || lvl}</p>
                    <p className="text-xs text-gray-500">{config.min} - {config.max} mata</p>
                  </div>
                </div>
                <span className="text-sm font-medium">{config.multiplier}x kredit</span>
              </div>
            ))}
          </div>
        </div>

        {/* Factor Breakdown */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* Positive Factors */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4 text-green-600">Faktor Positif</h3>
            <div className="space-y-3">
              <div className="flex justify-between"><span className="text-gray-600">Pesanan berjaya</span><span className="font-medium">{data?.successful_orders || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Bulan langganan</span><span className="font-medium">{data?.subscription_months || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Rujukan</span><span className="font-medium">{data?.referral_count || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Pertikaian sah</span><span className="font-medium">{data?.legitimate_disputes || 0}</span></div>
            </div>
          </div>

          {/* Negative Factors */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4 text-red-600">Faktor Negatif</h3>
            <div className="space-y-3">
              <div className="flex justify-between"><span className="text-gray-600">Pertikaian palsu</span><span className="font-medium">{data?.fraudulent_disputes || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Pertikaian ditolak</span><span className="font-medium">{data?.rejected_disputes || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Kegagalan bayaran</span><span className="font-medium">{data?.payment_failures || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-600">Pelanggaran terma</span><span className="font-medium">{data?.terms_violations || 0}</span></div>
            </div>
          </div>
        </div>

        {/* Tips */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-3">Tingkatkan Skor Anda</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <p>- Buat pesanan dan selesaikan dengan jayanya (+5 mata)</p>
            <p>- Kekalkan langganan aktif (+10 mata sebulan)</p>
            <p>- Jemput rakan menggunakan kod rujukan (+15 mata)</p>
            <p>- Elakkan pertikaian palsu (-50 mata)</p>
          </div>
        </div>

        {/* Score History */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h3 className="text-lg font-semibold">Sejarah Skor</h3>
          </div>
          {(!data?.history || data.history.length === 0) ? (
            <div className="p-8 text-center text-gray-500">Tiada sejarah perubahan skor</div>
          ) : (
            <div className="divide-y">
              {data.history.map((h) => (
                <div key={h.id} className="p-4 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">{h.change_reason}</p>
                    <p className="text-xs text-gray-400">{new Date(h.created_at).toLocaleDateString('ms-MY')}</p>
                  </div>
                  <div className="text-right">
                    <span className={`font-bold ${h.change_amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {h.change_amount >= 0 ? '+' : ''}{h.change_amount}
                    </span>
                    <p className="text-xs text-gray-400">{h.old_score} &rarr; {h.new_score}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

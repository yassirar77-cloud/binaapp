'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface Penalty {
  id: string
  penalty_type: string
  reason: string
  complaint_rate: number
  fine_amount: number
  is_active: boolean
  expires_at: string | null
  created_at: string
}

const penaltyConfig: Record<string, { label: string; color: string; bgColor: string; icon: string }> = {
  warning: {
    label: 'Amaran',
    color: 'text-yellow-800',
    bgColor: 'bg-yellow-50 border-yellow-200',
    icon: '!'
  },
  fine: {
    label: 'Denda',
    color: 'text-orange-800',
    bgColor: 'bg-orange-50 border-orange-200',
    icon: '$'
  },
  suspension: {
    label: 'Penggantungan',
    color: 'text-red-800',
    bgColor: 'bg-red-50 border-red-200',
    icon: 'X'
  },
  permanent_ban: {
    label: 'Diharamkan',
    color: 'text-red-900',
    bgColor: 'bg-red-100 border-red-300',
    icon: '!'
  }
}

interface PenaltyBannerProps {
  onAppeal?: (penaltyId: string) => void
}

export default function PenaltyBanner({ onAppeal }: PenaltyBannerProps) {
  const router = useRouter()
  const [penalties, setPenalties] = useState<Penalty[]>([])
  const [loading, setLoading] = useState(true)
  const [appealingId, setAppealingId] = useState<string | null>(null)
  const [appealReason, setAppealReason] = useState('')
  const [showAppealForm, setShowAppealForm] = useState(false)

  useEffect(() => {
    loadPenalties()
  }, [])

  const loadPenalties = async () => {
    try {
      const token = getStoredToken()
      if (!token) return

      const response = await fetch(`${API_BASE_URL}/api/v1/penalties/my-penalties`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const d = await response.json()
        const active = (d.data || []).filter((p: Penalty) => p.is_active)
        setPenalties(active)
      }
    } catch (err) {
      console.error('Error loading penalties:', err)
    } finally {
      setLoading(false)
    }
  }

  const submitAppeal = async () => {
    if (!appealingId || !appealReason.trim()) return

    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/penalties/${appealingId}/appeal`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: appealReason })
      })

      if (response.ok) {
        alert('Rayuan berjaya dikemukakan!')
        setShowAppealForm(false)
        setAppealingId(null)
        setAppealReason('')
        if (onAppeal) onAppeal(appealingId)
      } else {
        const err = await response.json()
        alert(err.detail || 'Gagal menghantar rayuan')
      }
    } catch (err) {
      console.error('Error:', err)
    }
  }

  if (loading || penalties.length === 0) return null

  return (
    <div className="space-y-3">
      {penalties.map((penalty) => {
        const config = penaltyConfig[penalty.penalty_type] || penaltyConfig.warning
        return (
          <div key={penalty.id} className={`border rounded-lg p-4 ${config.bgColor}`}>
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-lg ${config.color} bg-white/50`}>
                  {config.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${config.color}`}>{config.label}</span>
                    {penalty.fine_amount > 0 && (
                      <span className="text-red-600 font-semibold text-sm">RM{penalty.fine_amount.toFixed(2)}</span>
                    )}
                  </div>
                  <p className={`text-sm mt-1 ${config.color}`}>{penalty.reason}</p>
                  {penalty.expires_at && (
                    <p className="text-xs text-gray-500 mt-1">
                      Tamat: {new Date(penalty.expires_at).toLocaleDateString('ms-MY')}
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={() => {
                  setAppealingId(penalty.id)
                  setShowAppealForm(true)
                }}
                className="text-blue-600 text-sm hover:underline whitespace-nowrap"
              >
                Rayu
              </button>
            </div>
          </div>
        )
      })}

      {/* Appeal Form Modal */}
      {showAppealForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold mb-3">Hantar Rayuan</h3>
            <p className="text-sm text-gray-600 mb-4">Jelaskan mengapa anda merasakan penalti ini tidak adil.</p>
            <textarea
              value={appealReason}
              onChange={(e) => setAppealReason(e.target.value)}
              rows={4}
              placeholder="Nyatakan sebab rayuan anda..."
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={submitAppeal}
                disabled={!appealReason.trim()}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium disabled:opacity-50 transition-colors"
              >
                Hantar Rayuan
              </button>
              <button
                onClick={() => { setShowAppealForm(false); setAppealingId(null); setAppealReason('') }}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 rounded-lg font-medium transition-colors"
              >
                Batal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

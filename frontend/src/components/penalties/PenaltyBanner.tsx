'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'
import { AppModal } from '@/components/ui/AppModal'

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

const penaltyConfig: Record<string, { label: string; accent: string; bg: string; icon: string }> = {
  warning: {
    label: 'Amaran',
    accent: 'text-warn-400',
    bg: 'border-warn-400/20 bg-warn-400/[0.08]',
    icon: '!'
  },
  fine: {
    label: 'Denda',
    accent: 'text-warn-400',
    bg: 'border-warn-400/25 bg-warn-400/[0.10]',
    icon: '$'
  },
  suspension: {
    label: 'Penggantungan',
    accent: 'text-err-400',
    bg: 'border-err-400/20 bg-err-400/[0.08]',
    icon: 'X'
  },
  permanent_ban: {
    label: 'Diharamkan',
    accent: 'text-err-400',
    bg: 'border-err-400/30 bg-err-400/[0.12]',
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
        toast.success('Rayuan berjaya dikemukakan!')
        setShowAppealForm(false)
        setAppealingId(null)
        setAppealReason('')
        if (onAppeal) onAppeal(appealingId)
      } else {
        const err = await response.json()
        toast.error(err.detail || 'Gagal menghantar rayuan')
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
          <div key={penalty.id} className={`rounded-2xl border p-4 ${config.bg}`}>
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full bg-white/[0.06] text-lg font-bold ${config.accent}`}>
                  {config.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${config.accent}`}>{config.label}</span>
                    {penalty.fine_amount > 0 && (
                      <span className="text-sm font-semibold text-err-400">RM{penalty.fine_amount.toFixed(2)}</span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-white/70">{penalty.reason}</p>
                  {penalty.expires_at && (
                    <p className="mt-1 text-xs text-white/40">
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
                className="whitespace-nowrap text-sm font-medium text-volt-400 hover:text-volt-300"
              >
                Rayu
              </button>
            </div>
          </div>
        )
      })}

      {/* Appeal Form Modal */}
      <AppModal
        open={showAppealForm}
        onClose={() => { setShowAppealForm(false); setAppealingId(null); setAppealReason('') }}
        variant="warning"
        title="Hantar Rayuan"
        description="Jelaskan mengapa anda merasakan penalti ini tidak adil."
        primaryLabel="Hantar Rayuan"
        onPrimary={submitAppeal}
        secondaryLabel="Batal"
        onSecondary={() => { setShowAppealForm(false); setAppealingId(null); setAppealReason('') }}
      >
        <textarea
          value={appealReason}
          onChange={(e) => setAppealReason(e.target.value)}
          rows={4}
          placeholder="Nyatakan sebab rayuan anda..."
          className="w-full rounded-xl border border-white/[0.12] bg-white/[0.04] px-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-volt-400/40"
        />
      </AppModal>
    </div>
  )
}

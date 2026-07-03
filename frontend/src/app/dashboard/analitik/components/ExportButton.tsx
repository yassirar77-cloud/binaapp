'use client'

import { useState } from 'react'
import { Download, Lock } from 'lucide-react'
import toast from 'react-hot-toast'

import { getApiAuthToken } from '@/lib/supabase'

// Same base + fallback as lib/api.ts's apiFetch — otherwise, with
// NEXT_PUBLIC_API_URL unset, data loads (apiFetch hits onrender) but a
// relative export URL would hit the frontend origin and 404.
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface Props {
  websiteId: string
  days: number
  tier: string
  /** Open the upgrade prompt when a non-Pro merchant taps export */
  onLockedClick: () => void
}

/** CSV export — visible to everyone, functional on Pro. The backend
 *  enforces the plan again (403 tier_required), this is just honest UI. */
export default function ExportButton({ websiteId, days, tier, onLockedClick }: Props) {
  const [downloading, setDownloading] = useState(false)
  const isPro = ['pro', 'enterprise'].includes((tier || '').toLowerCase())

  const download = async () => {
    if (!isPro) {
      onLockedClick()
      return
    }
    try {
      setDownloading(true)
      const token = await getApiAuthToken()
      if (!token) {
        toast.error('Sesi tamat. Sila log masuk semula.')
        return
      }
      const res = await fetch(
        `${API_URL}/api/v1/analytics/export?website_id=${websiteId}&days=${days}&dataset=orders`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (!res.ok) throw new Error(`Export failed (${res.status})`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `analitik-pesanan-${new Date().toISOString().split('T')[0]}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('[analitik] export error:', e)
      toast.error('Gagal mengeksport CSV. Sila cuba lagi.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={download}
      disabled={downloading}
      className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
        isPro
          ? 'bg-[#C7FF3D] text-[#0B0B15] hover:bg-[#d4ff66] disabled:opacity-60'
          : 'bg-white/[0.05] text-white/40 hover:text-white/60'
      }`}
    >
      {isPro ? <Download size={13} strokeWidth={2} /> : <Lock size={12} strokeWidth={2} />}
      {downloading ? 'Memuat turun…' : 'Eksport CSV'}
    </button>
  )
}

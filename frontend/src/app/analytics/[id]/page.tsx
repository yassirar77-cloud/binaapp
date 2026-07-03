'use client'

/**
 * Legacy analytics route — the per-website analytics page moved to the
 * Analitik dashboard tab. Old bookmarks land here; forward them along
 * with the selected website.
 */

import { useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'

export default function LegacyAnalyticsRedirect() {
  const params = useParams()
  const router = useRouter()

  useEffect(() => {
    const id = params?.id as string | undefined
    router.replace(id ? `/dashboard/analitik?website=${id}` : '/dashboard/analitik')
  }, [params, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0B0B15]">
      <p className="text-sm text-white/50">Membawa anda ke Analitik…</p>
    </div>
  )
}

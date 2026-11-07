'use client'

/**
 * "Draf sedia diterbitkan" — the dashboard's way to the publish dialog.
 *
 * The dashboard's own site list reads Supabase directly, which returns only
 * published rows, so a generated draft never showed there and the merchant
 * could not find where to publish it (agp, draft 258b05b9). The banner asks
 * the API (the same list My Projects uses) for publishable drafts and links
 * each to My Projects with its "Terbitkan ke subdomain" dialog open.
 */

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getStoredToken } from '@/lib/supabase'
import { publishLink, publishableDrafts, type SiteRow } from '@/lib/draftPublish'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface ListedSite extends SiteRow {
  created_at?: string
}

function shortDate(iso?: string): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('ms-MY', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export default function DraftPublishBanner() {
  const [drafts, setDrafts] = useState<ListedSite[]>([])

  useEffect(() => {
    const token = getStoredToken()
    if (!token) return
    let cancelled = false
    fetch(`${API_BASE}/api/v1/websites/`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: ListedSite[]) => {
        if (!cancelled) setDrafts(publishableDrafts(rows || []) as ListedSite[])
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  if (drafts.length === 0) return null

  return (
    <section
      aria-label="Draf sedia diterbitkan"
      className="relative z-10 mx-4 md:mx-auto md:max-w-7xl md:px-6 mt-4 mb-2"
    >
      <div className="rounded-2xl border border-[#C7FF3D]/30 bg-[#C7FF3D]/[0.06] p-4">
        <h2 className="font-geist font-semibold text-sm text-white mb-1">Draf sedia diterbitkan</h2>
        <p className="text-xs text-white/60 mb-3">Terbitkan draf ini untuk menggantikan laman langsung anda.</p>
        <ul className="flex flex-col gap-2">
          {drafts.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-white/[0.04] px-3 py-2.5">
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium text-white">{d.business_name}</span>
                <span className="block font-geist-mono text-[10.5px] text-white/40">
                  {shortDate(d.created_at)} · {d.id.slice(0, 8)}
                </span>
              </span>
              <Link
                href={publishLink(d.id)}
                className="shrink-0 rounded-[9px] bg-[#C7FF3D] px-3 py-2 text-xs font-semibold text-[#0B0B15] hover:bg-[#d4ff66] transition-colors min-h-[36px] inline-flex items-center"
              >
                Terbitkan ke subdomain
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

'use client'

import { BarChart3 } from 'lucide-react'

/** Friendly per-section empty state for merchants with no data yet.
 *  Same visual pattern as pesanan/components/EmptyState.tsx. */
export default function AnalitikEmptyState({
  heading = 'Belum ada data lagi',
  sub = 'Kongsi laman anda untuk mula menerima pelawat dan pesanan.',
}: {
  heading?: string
  sub?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-4">
      <div className="mb-4 inline-flex items-center justify-center w-14 h-14 rounded-full bg-white/[0.04] ring-1 ring-white/[0.08] text-white/50">
        <BarChart3 size={22} strokeWidth={1.5} />
      </div>
      <p className="text-sm text-white/70 font-geist">{heading}</p>
      <p className="mt-1 text-xs text-white/40 font-geist max-w-xs">{sub}</p>
    </div>
  )
}

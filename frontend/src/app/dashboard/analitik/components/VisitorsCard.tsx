'use client'

import Sparkline from '@/components/dashboard-new/Sparkline'

import type { VisitorsResponse } from '../lib/analytics'
import AnalitikEmptyState from './AnalitikEmptyState'

/** Website visitors: uniques/views sparkline, device split, top pages,
 *  traffic sources — all from the PDPA rollup tables. */
export default function VisitorsCard({ visitors }: { visitors: VisitorsResponse }) {
  const hasData = visitors.totals.total_views > 0
  const points = visitors.series.map((p) => ({ value: p.total_views, label: p.date }))
  const deviceTotal =
    visitors.devices.mobile + visitors.devices.tablet + visitors.devices.desktop

  return (
    <div className="dash-surface p-5">
      <div className="dash-eyebrow mb-4">Pelawat Website</div>
      {!hasData ? (
        <AnalitikEmptyState
          heading="Tiada pelawat direkodkan lagi"
          sub="Kongsi pautan website anda — statistik pelawat akan muncul di sini. Pelawat yang memilih 'Do Not Track' tidak dikira."
        />
      ) : (
        <>
          <div className="flex items-end justify-between gap-4 mb-5">
            <div>
              <div className="font-geist font-bold dash-tnum text-[32px] leading-none text-white mb-1.5">
                {visitors.totals.unique_visitors}
              </div>
              <div className="text-[12px] text-white/40">
                pelawat unik · {visitors.totals.total_views} paparan
              </div>
            </div>
            <Sparkline
              points={points.slice(-14)}
              color="rgba(199,255,61,0.35)"
              highlightColor="#C7FF3D"
              width={150}
              height={44}
            />
          </div>

          {/* Device split */}
          {deviceTotal > 0 && (
            <div className="mb-5">
              <div className="flex h-1.5 rounded-full overflow-hidden bg-white/[0.05] mb-2">
                <div
                  style={{
                    width: `${(visitors.devices.mobile / deviceTotal) * 100}%`,
                    background: '#C7FF3D',
                  }}
                />
                <div
                  style={{
                    width: `${(visitors.devices.tablet / deviceTotal) * 100}%`,
                    background: 'rgba(199,255,61,0.5)',
                  }}
                />
                <div
                  style={{
                    width: `${(visitors.devices.desktop / deviceTotal) * 100}%`,
                    background: '#4F3DFF',
                  }}
                />
              </div>
              <div className="flex gap-4 text-[11px] text-white/45 font-geist-mono">
                <span>📱 Mudah alih {visitors.devices.mobile}</span>
                <span>Tablet {visitors.devices.tablet}</span>
                <span>💻 Desktop {visitors.devices.desktop}</span>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 dash-divider pt-4">
            <div>
              <div className="text-[10px] font-geist-mono uppercase tracking-[0.08em] text-white/35 mb-2">
                Halaman Popular
              </div>
              <ul className="space-y-1.5">
                {visitors.top_pages.slice(0, 5).map((p) => (
                  <li
                    key={p.page_path}
                    className="flex justify-between gap-3 text-[12px]"
                  >
                    <span className="text-white/70 truncate">{p.page_path}</span>
                    <span className="dash-tnum text-white/45 shrink-0">{p.views}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-[10px] font-geist-mono uppercase tracking-[0.08em] text-white/35 mb-2">
                Sumber Trafik
              </div>
              <ul className="space-y-1.5">
                {visitors.top_referrers.slice(0, 5).map((r) => (
                  <li key={r.source} className="flex justify-between gap-3 text-[12px]">
                    <span className="text-white/70 truncate">
                      {r.source === 'direct' ? 'Terus / Direct' : r.source}
                    </span>
                    <span className="dash-tnum text-white/45 shrink-0">{r.views}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

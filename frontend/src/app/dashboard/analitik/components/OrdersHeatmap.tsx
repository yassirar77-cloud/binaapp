'use client'

import {
  DOW_LABELS_BM,
  buildHeatmapGrid,
  heatmapOpacity,
  type HeatmapCell,
} from '../lib/analytics'
import AnalitikEmptyState from './AnalitikEmptyState'

/** 7×24 "waktu puncak" grid — cell intensity = order count (volt scale).
 *  A plain CSS grid; recharts has no heatmap primitive and this stays
 *  exactly on the design system. */
export default function OrdersHeatmap({ cells }: { cells: HeatmapCell[] }) {
  const { rows, max } = buildHeatmapGrid(cells)

  return (
    <div className="dash-surface p-5">
      <div className="dash-eyebrow mb-1">Waktu Puncak Pesanan</div>
      <p className="text-xs text-white/40 mb-4">Bilangan pesanan mengikut hari dan jam</p>
      {max === 0 ? (
        <AnalitikEmptyState
          heading="Belum cukup data"
          sub="Corak waktu puncak akan terbentuk selepas beberapa pesanan diterima."
        />
      ) : (
        <div className="overflow-x-auto">
          <div className="min-w-[560px]">
            {rows.map((row, dow) => (
              <div key={dow} className="flex items-center gap-1 mb-1">
                <span className="w-8 shrink-0 text-[10px] font-geist-mono text-white/40">
                  {DOW_LABELS_BM[dow]}
                </span>
                {row.map((count, hour) => (
                  <div
                    key={hour}
                    title={`${DOW_LABELS_BM[dow]} ${hour}:00 — ${count} pesanan`}
                    className="h-4 flex-1 rounded-[3px] bg-white/[0.04]"
                    style={
                      count > 0
                        ? { background: `rgba(199,255,61,${heatmapOpacity(count, max)})` }
                        : undefined
                    }
                  />
                ))}
              </div>
            ))}
            <div className="flex items-center gap-1 mt-1 pl-9">
              {[0, 6, 12, 18, 23].map((h, i, arr) => (
                <span
                  key={h}
                  className="text-[10px] font-geist-mono text-white/30"
                  style={{ marginLeft: i === 0 ? 0 : 'auto' }}
                >
                  {h}:00{i === arr.length - 1 ? '' : ''}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

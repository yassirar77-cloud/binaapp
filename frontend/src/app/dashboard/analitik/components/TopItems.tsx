'use client'

import { formatRM, type TopItem } from '../lib/analytics'
import AnalitikEmptyState from './AnalitikEmptyState'

/** Top 10 menu items as a horizontal bar list (volt bars, tabular nums). */
export default function TopItems({ items }: { items: TopItem[] }) {
  const maxQty = items.length ? Math.max(...items.map((i) => i.quantity)) : 0

  return (
    <div className="dash-surface p-5">
      <div className="dash-eyebrow mb-4">Menu Paling Laris</div>
      {items.length === 0 ? (
        <AnalitikEmptyState
          heading="Tiada jualan menu lagi"
          sub="Item paling laris anda akan disenaraikan di sini."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((item, idx) => (
            <li key={item.item_name}>
              <div className="flex items-baseline justify-between gap-3 mb-1">
                <span className="text-[13px] text-white/80 truncate">
                  <span className="font-geist-mono text-[11px] text-white/35 mr-2">
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  {item.item_name}
                </span>
                <span className="dash-tnum text-[12px] text-white/50 shrink-0">
                  {item.quantity}x · {formatRM(item.revenue)}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${maxQty > 0 ? (item.quantity / maxQty) * 100 : 0}%`,
                    background:
                      idx === 0 ? '#C7FF3D' : 'rgba(199,255,61,0.45)',
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

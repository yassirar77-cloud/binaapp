'use client'

import { formatRM, type RiderRow, type ZoneRow } from '../lib/analytics'
import AnalitikEmptyState from './AnalitikEmptyState'

/** Zon Penghantaran + Prestasi Penghantar tables (shared styling). */

function Table({
  headers,
  children,
}: {
  headers: string[]
  children: React.ReactNode
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="pb-2 pr-4 text-[10px] font-geist-mono uppercase tracking-[0.08em] text-white/35 font-medium whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="text-[13px] text-white/75">{children}</tbody>
      </table>
    </div>
  )
}

const rowClass = 'border-t border-white/[0.06]'
const cellClass = 'py-2.5 pr-4 whitespace-nowrap'

export function ZoneTable({ zones }: { zones: ZoneRow[] }) {
  return (
    <div className="dash-surface p-5">
      <div className="dash-eyebrow mb-4">Zon Penghantaran</div>
      {zones.length === 0 ? (
        <AnalitikEmptyState
          heading="Tiada penghantaran lagi"
          sub="Statistik zon akan muncul selepas pesanan penghantaran pertama."
        />
      ) : (
        <Table headers={['Zon', 'Pesanan', 'Jualan', 'Caj Hantar', '% Batal']}>
          {zones.map((z) => (
            <tr key={z.zone} className={rowClass}>
              <td className={`${cellClass} text-white/90`}>{z.zone}</td>
              <td className={`${cellClass} dash-tnum`}>{z.orders}</td>
              <td className={`${cellClass} dash-tnum`}>{formatRM(z.revenue)}</td>
              <td className={`${cellClass} dash-tnum`}>{formatRM(z.delivery_fees)}</td>
              <td className={`${cellClass} dash-tnum`}>
                <span className={z.cancel_rate_pct > 20 ? 'text-[#FF5A5F]' : ''}>
                  {z.cancel_rate_pct}%
                </span>
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}

export function RiderTable({ riders }: { riders: RiderRow[] }) {
  return (
    <div className="dash-surface p-5">
      <div className="dash-eyebrow mb-4">Prestasi Penghantar</div>
      {riders.length === 0 ? (
        <AnalitikEmptyState
          heading="Tiada data penghantar"
          sub="Prestasi penghantar akan dipaparkan selepas penghantaran pertama selesai."
        />
      ) : (
        <Table headers={['Penghantar', 'Hantaran', 'Purata Masa', 'Rating']}>
          {riders.map((r) => (
            <tr key={r.rider_id} className={rowClass}>
              <td className={`${cellClass} text-white/90`}>{r.name}</td>
              <td className={`${cellClass} dash-tnum`}>{r.deliveries}</td>
              <td className={`${cellClass} dash-tnum`}>
                {r.avg_delivery_minutes !== null ? `${r.avg_delivery_minutes} min` : '—'}
              </td>
              <td className={`${cellClass} dash-tnum`}>
                {r.rating !== null && r.rating !== undefined ? `★ ${r.rating}` : '—'}
              </td>
            </tr>
          ))}
        </Table>
      )}
    </div>
  )
}

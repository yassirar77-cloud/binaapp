'use client'

import type { TrackedOrder, TrackedOrderItem } from '../tracking-api'

interface OrderContextCardProps {
  order: TrackedOrder
  items: TrackedOrderItem[]
}

/**
 * "Pesanan yang bermasalah" recap card so the customer can confirm
 * we know which order they're disputing. Mirrors the design's compact
 * order-context block — order number + date + items summary + total.
 */
export function OrderContextCard({ order, items }: OrderContextCardProps) {
  const itemSummary = items
    .map((it) => `${it.name} ×${it.quantity}`)
    .join(', ')

  const placedAt = order.createdAt ? formatPlacedAt(order.createdAt) : ''

  return (
    <div className="dp-sec">
      <h3>Pesanan yang bermasalah</h3>
      <div className="order-ctx">
        <div className="top">
          <span className="ord-num">#{order.orderNumber}</span>
          {placedAt && <span>{placedAt}</span>}
        </div>
        {itemSummary && <div className="items">{itemSummary}</div>}
        <div className="total">RM {order.totalAmount.toFixed(2)}</div>
      </div>
    </div>
  )
}

const MONTHS_BM = [
  'jan', 'feb', 'mac', 'apr', 'mei', 'jun',
  'jul', 'ogs', 'sep', 'okt', 'nov', 'dis',
]

/** Format an ISO timestamp as "2 mei, 7:42 ptg" — same shape as the design. */
function formatPlacedAt(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const day = d.getDate()
  const month = MONTHS_BM[d.getMonth()] ?? ''
  const hours24 = d.getHours()
  const hour = ((hours24 + 11) % 12) + 1
  const minute = String(d.getMinutes()).padStart(2, '0')
  const period = hours24 >= 12 ? 'ptg' : 'pg'
  return `${day} ${month}, ${hour}:${minute} ${period}`
}

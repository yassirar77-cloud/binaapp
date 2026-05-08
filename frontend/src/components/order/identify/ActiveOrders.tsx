'use client'

import Link from 'next/link'
import { Package } from 'lucide-react'
import type { ActiveOrder } from '../api'

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  pending: { label: 'Menunggu', className: 'pill pending' },
  confirmed: { label: 'Disahkan', className: 'pill confirmed' },
  preparing: { label: 'Sedang disediakan', className: 'pill preparing' },
  ready: { label: 'Siap', className: 'pill ready' },
  picked_up: { label: 'Diambil rider', className: 'pill picked-up' },
  delivering: { label: 'Dalam penghantaran', className: 'pill delivering' },
}

function StatusPill({ status }: { status: string }) {
  const info = STATUS_LABELS[status] ?? { label: status, className: 'pill' }
  return <span className={info.className}>{info.label}</span>
}

interface ActiveOrdersProps {
  orders: ActiveOrder[]
}

/**
 * Shows the customer's active (non-terminal) orders so they can recover
 * a tracking link without needing the WhatsApp message.
 */
export function ActiveOrders({ orders }: ActiveOrdersProps) {
  if (orders.length === 0) return null

  return (
    <div className="active-orders fade-up" aria-live="polite">
      <div className="ao-header">
        <Package size={16} strokeWidth={2} aria-hidden="true" />
        <span>
          Anda ada {orders.length} pesanan aktif
        </span>
      </div>

      <ul className="ao-list">
        {orders.map((o) => (
          <li key={o.order_number} className="ao-card">
            <div className="ao-top">
              <span className="ao-num">#{o.order_number}</span>
              <StatusPill status={o.status} />
            </div>
            <div className="ao-meta">
              <span>RM{o.total.toFixed(2)}</span>
            </div>
            <Link
              href={`/order/tracking/${encodeURIComponent(o.order_number)}`}
              className="ao-track-btn"
            >
              Track Pesanan
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

'use client'

import { useRestaurant } from '../ThemeProvider'
import { isTerminalStatus } from '../status-mapper'

interface TrackingHeaderProps {
  orderNumber: string
  status: string
}

/**
 * Top of the tracking page: order number + Live pulse badge (hidden
 * once the order reaches a terminal state) + restaurant identity row.
 */
export function TrackingHeader({ orderNumber, status }: TrackingHeaderProps) {
  const restaurant = useRestaurant()
  const live = !isTerminalStatus(status)

  return (
    <>
      <div className="tk-header">
        <div className="ord-id">
          <span className="lbl">Pesanan</span>
          <span className="num">#{orderNumber}</span>
        </div>
        {live && (
          <span className="live-badge">
            <span className="pulse-dot" aria-hidden="true" />
            Live
          </span>
        )}
      </div>

      <div className="ord-resto">
        <div className="mini" aria-hidden="true">{restaurant.initials}</div>
        <span className="nm">{restaurant.name}</span>
      </div>
    </>
  )
}

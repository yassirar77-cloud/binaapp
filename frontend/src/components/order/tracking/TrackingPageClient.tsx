'use client'

import dynamic from 'next/dynamic'
import { Check, FileQuestion } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button } from '../primitives'
import {
  isDeliveredStatus,
  isTerminalStatus,
  pollingIntervalMs,
  shouldShowMap,
} from '../status-mapper'
import {
  fetchTrackedOrder,
  TrackOrderError,
  type TrackedOrderDetail,
} from '../tracking-api'
import { ActionButtons } from './ActionButtons'
import { ETAReadout } from './ETAReadout'
import { OrderDetailsAccordion } from './OrderDetailsAccordion'
import { PostDeliveryRating } from './PostDeliveryRating'
import { ProgressSteps } from './ProgressSteps'
import { RiderCard } from './RiderCard'
import { TrackingHeader } from './TrackingHeader'

// Leaflet uses `window` and ships ~150kb of bundle weight — load it
// only on the client and only when this component is actually mounted.
const DeliveryMap = dynamic(
  () => import('./DeliveryMap').then((m) => m.DeliveryMap),
  {
    ssr: false,
    loading: () => (
      <div className="map-card unavailable">
        <span>Memuatkan peta…</span>
      </div>
    ),
  }
)

interface TrackingPageClientProps {
  orderNumber: string
}

/**
 * Orchestrates the tracking page.
 *
 * Polling strategy (per pre-locked decision):
 *   - Initial fetch on mount.
 *   - Re-fetch every 15s while status is non-terminal AND not en-route.
 *   - Re-fetch every 10s while status is `picked_up` or `delivering`
 *     (rider movement on the map needs tighter cadence).
 *   - Stop polling entirely once status is terminal (delivered /
 *     completed / cancelled / rejected).
 *   - Always cancel + restart the timer when status changes so the
 *     interval reflects the new state.
 *
 * Toggles the `tracking-route` class on `.order-flow` so the page
 * background flips to var(--bg-soft).
 *
 * Polling errors are logged to the console but do NOT surface to the
 * customer — a transient blip shouldn't drop them out of the live
 * view. The "not found" 404 is the only error we hard-render.
 */
export function TrackingPageClient({ orderNumber }: TrackingPageClientProps) {
  const [data, setData] = useState<TrackedOrderDetail | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // ---- Toggle the page-background class.
  useEffect(() => {
    const flow = document.querySelector('.order-flow')
    if (!flow) return
    flow.classList.add('tracking-route')
    return () => flow.classList.remove('tracking-route')
  }, [])

  // ---- Polling effect. Re-derives interval whenever the status
  //      changes; clears + reschedules cleanly on every status flip.
  useEffect(() => {
    let alive = true

    const tick = async () => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      try {
        const next = await fetchTrackedOrder(orderNumber, controller.signal)
        if (!alive || controller.signal.aborted) return
        setData(next)
        setNotFound(false)
        setLoading(false)
      } catch (err) {
        if (!alive || controller.signal.aborted) return
        if (err instanceof TrackOrderError && err.status === 404) {
          setNotFound(true)
          setLoading(false)
          return
        }
        // Transient — log and let the next tick try again.
        // eslint-disable-next-line no-console
        console.error('[order/track] poll failed:', err)
        setLoading(false)
      }
    }

    // Initial fetch.
    void tick()

    // Schedule the next tick. Re-runs whenever the status changes
    // (which is in our `data` dep below) so the interval picks up
    // the new cadence.
    const status = data?.order.status
    if (!isTerminalStatus(status)) {
      const intervalMs = pollingIntervalMs(status)
      intervalRef.current = setInterval(() => {
        void tick()
      }, intervalMs)
    }

    return () => {
      alive = false
      if (intervalRef.current) clearInterval(intervalRef.current)
      abortRef.current?.abort()
    }
  }, [orderNumber, data?.order.status])

  // ---- Render branches.
  if (loading && !data && !notFound) {
    return (
      <div style={{ padding: '40px 20px', color: 'var(--fg-muted)', fontSize: 13 }}>
        Memuatkan pesanan…
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="tk-not-found">
        <div className="ic">
          <FileQuestion size={28} strokeWidth={1.5} aria-hidden="true" />
        </div>
        <h2>Pesanan tidak ditemui</h2>
        <p>
          Nombor pesanan #{orderNumber} tidak wujud atau telah dipadam.
          Sila semak semula nombor pesanan anda.
        </p>
        <div style={{ maxWidth: 220, margin: '0 auto' }}>
          <Button onClick={() => (window.location.href = '/order/menu')}>
            Lihat menu
          </Button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { order, items, rider, riderLocation, etaMinutes } = data
  const showMap = shouldShowMap(order.status)
  const cancelled = order.status === 'cancelled' || order.status === 'rejected'
  const delivered = isDeliveredStatus(order.status)

  return (
    <>
      <TrackingHeader orderNumber={order.orderNumber} status={order.status} />

      <ETAReadout status={order.status} etaMinutes={etaMinutes} />

      {!cancelled && (
        <div className="tk-hero" style={{ paddingTop: 0, paddingBottom: 8 }}>
          <ProgressSteps status={order.status} />
        </div>
      )}

      {cancelled && (
        <div className="cancelled-banner">
          <span>
            Pesanan ini telah dibatalkan. Hubungi restoran untuk maklumat lanjut.
          </span>
        </div>
      )}

      {delivered && (
        <div className="delivered-banner">
          <div className="ic" aria-hidden="true">
            <Check size={20} strokeWidth={2.4} />
          </div>
          <div className="body">
            <div className="nm">Pesanan sudah sampai!</div>
            <div className="nt">Selamat menjamu selera 🍽️</div>
          </div>
        </div>
      )}

      {showMap && order.deliveryLatitude != null && order.deliveryLongitude != null && (
        <div className="map-card">
          <DeliveryMap
            delivery={{
              lat: order.deliveryLatitude,
              lng: order.deliveryLongitude,
            }}
            rider={
              riderLocation
                ? { lat: riderLocation.latitude, lng: riderLocation.longitude }
                : null
            }
          />
        </div>
      )}

      {showMap && (order.deliveryLatitude == null || order.deliveryLongitude == null) && (
        <div className="map-card unavailable">
          <span>Peta tidak tersedia untuk pesanan ini.</span>
        </div>
      )}

      {rider && (rider.phone || rider.name) && (
        <RiderCard rider={rider} order={order} />
      )}

      <OrderDetailsAccordion order={order} items={items} />

      {delivered && <PostDeliveryRating enabled={false} />}

      {!delivered && (
        <ActionButtons orderNumber={order.orderNumber} />
      )}
    </>
  )
}

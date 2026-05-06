'use client'

import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef } from 'react'

interface DeliveryMapProps {
  delivery: { lat: number; lng: number }
  rider?: { lat: number; lng: number } | null
}

/**
 * Live tracking map. Renders:
 *   - delivery destination pin (always)
 *   - rider position pin (when GPS available — moves with each poll)
 *   - dashed line between the two so the customer sees the route
 *
 * Only mounted while `status === 'picked_up' | 'delivering'` per
 * shouldShowMap() in status-mapper.ts. Imported via `dynamic` with
 * `ssr: false` from the orchestrator so Leaflet's bundle isn't
 * loaded on the server pass.
 *
 * TODO(map): Smooth-interpolate the rider marker between polling
 *            updates instead of jumping. leaflet-realtime or a small
 *            requestAnimationFrame loop both work.
 *
 * TODO(map): Add restaurant pin once `websites` table grows
 *            lat/lng columns. For now we only show "where the rider
 *            is" → "where it's going".
 */
export function DeliveryMap({ delivery, rider }: DeliveryMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const deliveryMarkerRef = useRef<L.Marker | null>(null)
  const riderMarkerRef = useRef<L.Marker | null>(null)
  const routeLineRef = useRef<L.Polyline | null>(null)

  // ---- Init the map exactly once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: [delivery.lat, delivery.lng],
      zoom: 14,
      zoomControl: false,
      attributionControl: false,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map)

    L.control
      .attribution({ prefix: false, position: 'bottomright' })
      .addAttribution('© <a href="https://www.openstreetmap.org/copyright">OSM</a>')
      .addTo(map)

    deliveryMarkerRef.current = L.marker([delivery.lat, delivery.lng], {
      icon: makeIcon('delivery'),
      title: 'Lokasi penghantaran',
      keyboard: false,
    }).addTo(map)

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
      deliveryMarkerRef.current = null
      riderMarkerRef.current = null
      routeLineRef.current = null
    }
    // The map should rebuild only if the destination changes — rider
    // updates are applied via the second effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [delivery.lat, delivery.lng])

  // ---- Sync the rider marker + route polyline with each poll.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    if (rider) {
      const latLng: L.LatLngExpression = [rider.lat, rider.lng]
      if (riderMarkerRef.current) {
        riderMarkerRef.current.setLatLng(latLng)
      } else {
        riderMarkerRef.current = L.marker(latLng, {
          icon: makeIcon('rider'),
          title: 'Lokasi rider',
          keyboard: false,
        }).addTo(map)
      }

      const linePoints: L.LatLngExpression[] = [latLng, [delivery.lat, delivery.lng]]
      if (routeLineRef.current) {
        routeLineRef.current.setLatLngs(linePoints)
      } else {
        routeLineRef.current = L.polyline(linePoints, {
          color: getCssVar('--brand-primary') || '#E8501F',
          weight: 3,
          dashArray: '6 6',
          opacity: 0.85,
        }).addTo(map)
      }

      // Auto-fit so both markers stay visible.
      const bounds = L.latLngBounds([latLng, [delivery.lat, delivery.lng]])
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16, animate: true })
    } else {
      // Rider GPS missing — strip the marker + line and recenter on
      // the destination so the map still feels alive.
      if (riderMarkerRef.current) {
        map.removeLayer(riderMarkerRef.current)
        riderMarkerRef.current = null
      }
      if (routeLineRef.current) {
        map.removeLayer(routeLineRef.current)
        routeLineRef.current = null
      }
      map.setView([delivery.lat, delivery.lng], 14, { animate: true })
    }
    // We deliberately depend on the lat/lng primitives rather than
    // the `rider` object — re-running on every poll's new object
    // identity would jitter the map even when coords haven't changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rider?.lat, rider?.lng, delivery.lat, delivery.lng])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}

/* ----- Icon factory ----------------------------------------------------- */

function makeIcon(kind: 'delivery' | 'rider'): L.DivIcon {
  if (kind === 'delivery') {
    return L.divIcon({
      className: '',
      iconSize: [28, 34],
      iconAnchor: [14, 34],
      html: `
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="34" viewBox="0 0 24 28" fill="var(--brand-primary,#E8501F)" stroke="white" stroke-width="1.5">
          <path d="M12 1c5 0 9 4 9 9 0 7-9 17-9 17S3 17 3 10c0-5 4-9 9-9z"/>
          <circle cx="12" cy="10" r="3" fill="white" stroke="none"/>
        </svg>
      `,
    })
  }
  // Rider: circular avatar-style chip with a pulse ring.
  return L.divIcon({
    className: '',
    iconSize: [42, 42],
    iconAnchor: [21, 21],
    html: `
      <div style="position:relative;width:42px;height:42px;">
        <div style="position:absolute;inset:-2px;border-radius:999px;border:2px solid var(--brand-primary,#E8501F);opacity:0.55;"></div>
        <div style="position:absolute;inset:0;border-radius:999px;background:var(--brand-primary,#E8501F);color:white;display:flex;align-items:center;justify-content:center;border:3px solid white;box-shadow:0 4px 10px rgba(0,0,0,0.18);">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="5.5" cy="17.5" r="3.5"/>
            <circle cx="18.5" cy="17.5" r="3.5"/>
            <path d="M15 6h4l3 6h-4M2 13h13l3-7h-3"/>
          </svg>
        </div>
      </div>
    `,
  })
}

function getCssVar(name: string): string {
  if (typeof window === 'undefined') return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export default DeliveryMap

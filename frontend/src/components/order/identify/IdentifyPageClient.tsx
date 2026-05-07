'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { IdentifyForm } from './IdentifyForm'
import { useRestaurantStore } from '../restaurant-store'
import type { ResolvedRestaurant } from '../restaurant-store'
import { Spinner } from '../primitives'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

type Phase =
  | { kind: 'resolving' }
  | { kind: 'ready' }
  | { kind: 'error'; subdomain: string }

/**
 * Reads the `?r=` subdomain query parameter, resolves it to a restaurant
 * via the backend, and saves the result to the restaurant Zustand store.
 *
 * - If `?r=` is absent: skips resolution, keeps whatever is in the store
 *   (or DEFAULT_RESTAURANT fallback in the layout).
 * - If `?r=` is present and resolves: saves to store, renders IdentifyForm.
 * - If `?r=` is present but 404: shows inline error.
 */
export function IdentifyPageClient() {
  const searchParams = useSearchParams()
  const subdomain = searchParams.get('r')
  const setRestaurant = useRestaurantStore((s) => s.setRestaurant)
  const stored = useRestaurantStore((s) => s.restaurant)

  const [phase, setPhase] = useState<Phase>(() => {
    // If no ?r= param, skip resolution entirely
    if (!subdomain) return { kind: 'ready' }
    // If we already resolved this subdomain, skip fetch
    if (stored?.subdomain === subdomain) return { kind: 'ready' }
    return { kind: 'resolving' }
  })

  useEffect(() => {
    if (!subdomain) return
    if (stored?.subdomain === subdomain) return

    let cancelled = false

    async function resolve() {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/websites/by-domain/${encodeURIComponent(subdomain)}`
        )
        if (cancelled) return

        if (!res.ok) {
          setPhase({ kind: 'error', subdomain })
          return
        }

        const data = await res.json()
        const restaurant: ResolvedRestaurant = {
          id: data.id,
          name: data.name || data.business_name || subdomain,
          businessName: data.business_name || data.name || subdomain,
          subdomain: data.subdomain || subdomain,
          whatsappNumber: data.whatsapp_number || null,
          status: data.status || 'published',
        }
        setRestaurant(restaurant)
        setPhase({ kind: 'ready' })
      } catch {
        if (!cancelled) setPhase({ kind: 'error', subdomain })
      }
    }

    void resolve()
    return () => { cancelled = true }
  }, [subdomain, stored?.subdomain, setRestaurant])

  if (phase.kind === 'resolving') {
    return (
      <div className="phone-page">
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            minHeight: '60dvh',
          }}
        >
          <Spinner />
          <p style={{ opacity: 0.6 }}>Memuatkan restoran…</p>
        </div>
      </div>
    )
  }

  if (phase.kind === 'error') {
    return (
      <div className="phone-page">
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            minHeight: '60dvh',
            textAlign: 'center',
            padding: '0 24px',
          }}
        >
          <p style={{ fontSize: 18, fontWeight: 600 }}>
            Restoran &lsquo;{phase.subdomain}&rsquo; tidak ditemui
          </p>
          <p style={{ opacity: 0.6, fontSize: 14 }}>
            Sila semak pautan anda dan cuba lagi.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="phone-page">
      <IdentifyForm />
    </div>
  )
}

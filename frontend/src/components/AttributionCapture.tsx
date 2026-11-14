'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { captureAttribution, pingVisitOncePerDay } from '@/lib/attribution'

// Only the public marketing surface counts as a "visit". Dashboards, the
// rider app and the pages merchants' own customers use are product usage,
// not marketing traffic, and would drown the numbers.
const MARKETING_PATHS = new Set([
  '/',
  '/register',
  '/login',
  '/polisi-privasi',
  '/privacy-policy',
  '/terma-perkhidmatan',
  '/terms-of-service',
])

const AUTH_TOKEN_KEY = 'binaapp_auth_token'

function isSignedIn(): boolean {
  try {
    return Boolean(window.localStorage.getItem(AUTH_TOKEN_KEY))
  } catch {
    return false
  }
}

/**
 * Remembers how a visitor first reached binaapp.my and counts one visit per
 * browser per day. Renders nothing. See lib/attribution.ts.
 */
export default function AttributionCapture() {
  const pathname = usePathname()

  useEffect(() => {
    if (!pathname || !MARKETING_PATHS.has(pathname)) return
    if (isSignedIn()) return
    captureAttribution()
    pingVisitOncePerDay(API_BASE_URL)
  }, [pathname])

  return null
}

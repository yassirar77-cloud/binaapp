'use client'

import { Locate } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import {
  detectCurrentLocation,
  GeolocationDeniedError,
  GeolocationUnavailableError,
} from '../geocoding'

interface GeolocationHelperProps {
  /** Receives the resolved address string + lat/lng on success. */
  onResolved: (data: { address: string; latitude: number; longitude: number }) => void
}

/**
 * "Guna lokasi semasa" pill button. Resolves a Nominatim address from
 * the device GPS, surfaces toasts for the deny / unavailable / failure
 * paths, and falls back silently on network errors so the customer can
 * always type manually.
 */
export function GeolocationHelper({ onResolved }: GeolocationHelperProps) {
  const [busy, setBusy] = useState(false)

  const handleClick = async () => {
    if (busy) return
    setBusy(true)
    try {
      const result = await detectCurrentLocation()
      onResolved(result)
    } catch (err) {
      if (err instanceof GeolocationUnavailableError) {
        toast('Pelayar anda tidak menyokong lokasi', { icon: '⚠️' })
      } else if (err instanceof GeolocationDeniedError) {
        toast('Sila benarkan akses lokasi', { icon: '⚠️' })
      } else {
        toast('Tidak dapat mencari lokasi anda', { icon: '⚠️' })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <button type="button" className="geo-btn" onClick={handleClick} disabled={busy}>
      <Locate className="ic" size={14} aria-hidden="true" />
      {busy ? 'Mencari lokasi…' : 'Guna lokasi semasa'}
    </button>
  )
}

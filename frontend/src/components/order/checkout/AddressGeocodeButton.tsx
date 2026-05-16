'use client'

import { Search } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { geocodeAddress, GeocodeError } from '../checkout-api'

interface AddressGeocodeButtonProps {
  /** Current address text from the textarea. */
  text: string
  /**
   * Called when Nominatim resolves the address to coords. Shape mirrors
   * GeolocationHelper.onResolved so the parent can route both inputs
   * through the same handler.
   */
  onResolved: (data: { address: string; latitude: number; longitude: number }) => void
}

/**
 * "Semak alamat" pill button — paired with the typed-address textarea.
 *
 * Why a button and not auto-debounce: hitting the backend Nominatim
 * proxy on every keystroke would burn the shared rate limit and produce
 * partial-string false-negatives. An explicit click also gives the
 * customer a clear "I checked your address" moment to react to.
 *
 * Disabled until the text is at least 8 chars long — matches the
 * resolvedAddress validity rule the parent applies for the CTA.
 */
export function AddressGeocodeButton({ text, onResolved }: AddressGeocodeButtonProps) {
  const [busy, setBusy] = useState(false)
  const trimmed = text.trim()
  const disabled = busy || trimmed.length < 8

  const handleClick = async () => {
    if (disabled) return
    setBusy(true)
    // Client-side timeout so a hung request doesn't leave the button
    // stuck on "Menyemak alamat…" forever. 30s matches the coverage
    // useEffect — see CheckoutPageClient.
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30_000)
    try {
      const hit = await geocodeAddress(trimmed, controller.signal)
      if (hit.found && hit.lat != null && hit.lng != null) {
        onResolved({
          // Prefer Nominatim's resolved string when available — confirms
          // back to the user what was actually found.
          address: hit.displayName ?? trimmed,
          latitude: hit.lat,
          longitude: hit.lng,
        })
      } else {
        toast('Tidak dapat mencari alamat anda. Sila masukkan poskod dan bandar.', {
          icon: '⚠️',
        })
      }
    } catch (err) {
      const msg =
        err instanceof DOMException && err.name === 'AbortError'
          ? 'Permintaan masa tamat. Sila cuba lagi.'
          : err instanceof GeocodeError
            ? 'Pelayan geocode tidak dapat dihubungi. Sila cuba lagi.'
            : 'Tidak dapat menyemak alamat. Sila cuba lagi.'
      toast(msg, { icon: '⚠️' })
    } finally {
      clearTimeout(timeoutId)
      setBusy(false)
    }
  }

  return (
    <button
      type="button"
      className="geo-btn"
      onClick={handleClick}
      disabled={disabled}
    >
      <Search className="ic" size={14} aria-hidden="true" />
      {busy ? 'Menyemak alamat…' : 'Semak alamat'}
    </button>
  )
}

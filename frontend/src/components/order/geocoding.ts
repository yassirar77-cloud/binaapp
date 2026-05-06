/**
 * Reverse geocoding helper for the checkout page.
 *
 * Uses Nominatim (OpenStreetMap) — free, no API key required, and
 * returns a Bahasa-localized address when `accept-language=ms` is sent.
 * Per Nominatim's usage policy we identify ourselves with a custom
 * User-Agent string (frontend-side this is best-effort; some browsers
 * block setting User-Agent on fetch — Nominatim tolerates it via the
 * Referer header instead).
 *
 * TODO(geocoding): Consider Google Places autocomplete for better
 *                  address quality once an API key budget is available.
 */

export interface GeolocationResult {
  /** Display address — e.g. "12, Jalan Bukit Bintang, Kuala Lumpur 55100". */
  address: string
  latitude: number
  longitude: number
}

const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org'
const GEOLOCATION_TIMEOUT_MS = 10_000
const GEOLOCATION_MAX_AGE_MS = 60_000

export class GeolocationDeniedError extends Error {
  constructor() {
    super('Geolocation permission denied')
    this.name = 'GeolocationDeniedError'
  }
}

export class GeolocationUnavailableError extends Error {
  constructor() {
    super('Geolocation not available')
    this.name = 'GeolocationUnavailableError'
  }
}

/** Wrap navigator.geolocation in a Promise so we can `await` it. */
function getCurrentPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      reject(new GeolocationUnavailableError())
      return
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      timeout: GEOLOCATION_TIMEOUT_MS,
      maximumAge: GEOLOCATION_MAX_AGE_MS,
    })
  })
}

/**
 * Reverse-geocode a lat/lng to an address via Nominatim. Returns the
 * lat/lng formatted as a fallback string if the API call fails.
 */
async function reverseGeocode(lat: number, lng: number): Promise<string> {
  try {
    const url =
      `${NOMINATIM_BASE}/reverse` +
      `?lat=${lat}&lon=${lng}&format=json&accept-language=ms`
    const res = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) throw new Error(`Nominatim ${res.status}`)
    const data = (await res.json()) as { display_name?: string }
    if (data?.display_name) return data.display_name
  } catch {
    // fall through to coords fallback
  }
  return `Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`
}

/**
 * One-shot helper: gets the device location, then reverse-geocodes it.
 *
 * Throws `GeolocationDeniedError` when the user blocks the permission
 * prompt and `GeolocationUnavailableError` when the browser doesn't
 * support the API. Other failures (timeout, network) re-throw as-is.
 */
export async function detectCurrentLocation(): Promise<GeolocationResult> {
  let position: GeolocationPosition
  try {
    position = await getCurrentPosition()
  } catch (err) {
    if (err instanceof GeolocationUnavailableError) throw err
    // GeolocationPositionError.code === 1 means PERMISSION_DENIED
    const code = (err as { code?: number })?.code
    if (code === 1) throw new GeolocationDeniedError()
    throw err
  }
  const { latitude, longitude } = position.coords
  const address = await reverseGeocode(latitude, longitude)
  return { address, latitude, longitude }
}

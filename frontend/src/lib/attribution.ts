/**
 * First-touch marketing attribution for binaapp.my.
 *
 * The first time a browser lands on the site we remember how it got here
 * (utm_* tags, a referral code, the referring site, the landing path). The
 * signup form sends that along so each new account records its source, and
 * the backend counts one visit per browser per day by source.
 *
 * Privacy: this stores no visitor id — only the campaign labels that were
 * already in the URL the visitor opened. Visitors with Do Not Track or
 * Global Privacy Control on are neither stored nor counted.
 */

export interface Attribution {
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
  utm_content?: string
  ref?: string
  referrer?: string
  landing_path?: string
  first_seen?: string
}

export const ATTRIBUTION_KEY = 'binaapp_attribution'
export const VISIT_PING_KEY = 'binaapp_visit_ping'

const MAX_LEN = 200
const OWN_HOST = 'binaapp.my'

function clip(value: string | null | undefined): string | undefined {
  const v = (value || '').trim()
  return v ? v.slice(0, MAX_LEN) : undefined
}

/** Referrer URL → hostname, or undefined for none / our own site. */
export function externalReferrer(referrer: string | null | undefined): string | undefined {
  if (!referrer) return undefined
  try {
    const host = new URL(referrer).hostname.toLowerCase().replace(/^www\./, '')
    if (!host || host === OWN_HOST || host.endsWith(`.${OWN_HOST}`)) return undefined
    return host.slice(0, MAX_LEN)
  } catch {
    return undefined
  }
}

/** Pure: build the attribution record for one page load. */
export function buildAttribution(
  search: string,
  referrer: string | null | undefined,
  pathname: string,
  now: Date = new Date()
): Attribution {
  const params = new URLSearchParams(search)
  const out: Attribution = {
    utm_source: clip(params.get('utm_source')),
    utm_medium: clip(params.get('utm_medium')),
    utm_campaign: clip(params.get('utm_campaign')),
    utm_content: clip(params.get('utm_content')),
    ref: clip(params.get('ref')),
    referrer: externalReferrer(referrer),
    landing_path: clip(pathname) || '/',
    first_seen: now.toISOString(),
  }
  // Drop empty keys so the stored JSON and the request body stay small.
  ;(Object.keys(out) as (keyof Attribution)[]).forEach((k) => {
    if (out[k] === undefined) delete out[k]
  })
  return out
}

/** True when this page load carries campaign information worth keeping. */
export function hasCampaignSignal(a: Attribution): boolean {
  return Boolean(a.utm_source || a.utm_campaign || a.ref || a.referrer)
}

export function privacyOptOut(): boolean {
  if (typeof navigator === 'undefined') return true
  const nav = navigator as Navigator & { globalPrivacyControl?: boolean }
  const win = window as Window & { doNotTrack?: string }
  return nav.doNotTrack === '1' || win.doNotTrack === '1' || nav.globalPrivacyControl === true
}

/** The stored first-touch record, or null. Never throws. */
export function getAttribution(): Attribution | null {
  try {
    const raw = window.localStorage.getItem(ATTRIBUTION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? (parsed as Attribution) : null
  } catch {
    return null
  }
}

/**
 * Remember the first touch. A later visit never overwrites it — except that
 * a plain "direct" first touch is upgraded once a real campaign arrives, so
 * someone who typed the address and later clicked a TikTok link is credited
 * to TikTok rather than to nothing.
 */
export function captureAttribution(): Attribution | null {
  if (typeof window === 'undefined' || privacyOptOut()) return null
  try {
    const current = buildAttribution(
      window.location.search,
      document.referrer,
      window.location.pathname
    )
    const stored = getAttribution()
    if (stored && (hasCampaignSignal(stored) || !hasCampaignSignal(current))) {
      return stored
    }
    window.localStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(current))
    return current
  } catch {
    return null
  }
}

/** Local calendar day, used to send at most one visit ping per day. */
export function dayKey(now: Date = new Date()): string {
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${m}-${d}`
}

/**
 * Count this browser's visit once per day. The ping carries today's
 * campaign when there is one, else the remembered first touch.
 */
export function pingVisitOncePerDay(apiBase: string): void {
  if (typeof window === 'undefined' || privacyOptOut()) return
  try {
    const today = dayKey()
    if (window.localStorage.getItem(VISIT_PING_KEY) === today) return
    window.localStorage.setItem(VISIT_PING_KEY, today)

    const current = buildAttribution(
      window.location.search,
      document.referrer,
      window.location.pathname
    )
    const payload = hasCampaignSignal(current) ? current : getAttribution() || current
    const { first_seen: _ignored, ...body } = payload

    fetch(`${apiBase}/api/v1/marketing/visit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      keepalive: true,
    }).catch(() => {})
  } catch {
    // Storage blocked (private mode): skip silently.
  }
}

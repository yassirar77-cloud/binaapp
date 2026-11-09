/**
 * Apex domains a merchant can publish under. Must match the backend's
 * MAIN_DOMAIN + ALT_SITE_DOMAINS (backend/app/services/site_domains.py) and
 * the CHECK in migration 061. The first entry is the default.
 */
export const SITE_DOMAINS = ['binaapp.my', 'mysyg.com'] as const
export type SiteDomain = (typeof SITE_DOMAINS)[number]
export const DEFAULT_SITE_DOMAIN: SiteDomain = SITE_DOMAINS[0]

export function resolveSiteDomain(value?: string | null): SiteDomain {
  const v = (value || '').trim().toLowerCase().replace(/^\.+|\.+$/g, '')
  return (SITE_DOMAINS as readonly string[]).includes(v) ? (v as SiteDomain) : DEFAULT_SITE_DOMAIN
}

/** "kedai.mysyg.com" (no scheme) */
export function siteHost(subdomain: string, domain?: string | null): string {
  return `${subdomain}.${resolveSiteDomain(domain)}`
}

/** "https://kedai.mysyg.com" */
export function siteUrl(subdomain: string, domain?: string | null): string {
  return `https://${siteHost(subdomain, domain)}`
}

/** Host part of a full site URL, e.g. "https://kedai.mysyg.com" -> "kedai.mysyg.com". */
export function hostOf(url?: string | null): string | null {
  if (!url) return null
  try {
    return new URL(url).host
  } catch {
    return null
  }
}

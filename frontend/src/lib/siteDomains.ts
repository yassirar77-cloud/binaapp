/**
 * Apex domains a merchant can publish under. Must match the backend's
 * MAIN_DOMAIN + ALT_SITE_DOMAINS (backend/app/services/site_domains.py) and
 * the CHECK in migration 061. The first entry is the default.
 *
 * mysyg.com is not here: it is the surprise-wish product, served by the
 * backend (backend/app/middleware/wish_pages.py). With a single domain the
 * publish modal and My Projects show no domain picker.
 */
export const SITE_DOMAINS: readonly string[] = ['binaapp.my']
export const HAS_DOMAIN_CHOICE = SITE_DOMAINS.length > 1
export type SiteDomain = string
export const DEFAULT_SITE_DOMAIN: SiteDomain = SITE_DOMAINS[0]

export function resolveSiteDomain(value?: string | null): SiteDomain {
  const v = (value || '').trim().toLowerCase().replace(/^\.+|\.+$/g, '')
  return SITE_DOMAINS.includes(v) ? v : DEFAULT_SITE_DOMAIN
}

/** "kedai.binaapp.my" (no scheme) */
export function siteHost(subdomain: string, domain?: string | null): string {
  return `${subdomain}.${resolveSiteDomain(domain)}`
}

/** "https://kedai.binaapp.my" */
export function siteUrl(subdomain: string, domain?: string | null): string {
  return `https://${siteHost(subdomain, domain)}`
}

/** Host part of a full site URL, e.g. "https://kedai.binaapp.my" -> "kedai.binaapp.my". */
export function hostOf(url?: string | null): string | null {
  if (!url) return null
  try {
    return new URL(url).host
  } catch {
    return null
  }
}

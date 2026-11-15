/**
 * The canonical public origin of the marketing site.
 *
 * www.binaapp.my is the host that serves the pages; the bare binaapp.my
 * redirects to it. Canonical tags, the sitemap and robots.txt must all use
 * this exact origin — pointing them at the redirecting host gives search
 * engines URLs that never return a page.
 *
 * Links people type or share can stay as binaapp.my (the redirect keeps the
 * path and query string), so this is only for what crawlers read.
 */
export const SITE_URL = 'https://www.binaapp.my'

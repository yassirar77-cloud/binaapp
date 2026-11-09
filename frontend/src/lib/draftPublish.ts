/**
 * "Terbitkan ke subdomain" — publish one of my generated drafts OVER one of
 * my live sites, from My Projects.
 *
 * A draft made in another session (agp: generated, reviewed, approved) had
 * no way to go live: the create page only publishes the page it holds in
 * memory. The backend's replace mode (POST /api/publish with draft_id +
 * replace_website_id) resolves everything from the two rows server-side —
 * ownership, the draft's HTML re-pointed at the live row, its menu and
 * business fields — so the page sends only the two ids.
 *
 * Pure module (no React, no fetch) so the rules are unit-testable.
 */

import { siteHost } from './siteDomains'

export interface SiteRow {
  id: string
  business_name: string
  subdomain: string | null
  /** binaapp.my or mysyg.com */
  site_domain?: string | null
  status: string
  replaceable_draft?: boolean
}

/** Live sites a draft may replace: published, with a real subdomain. */
export function liveTargets(sites: SiteRow[]): SiteRow[] {
  return sites.filter(
    (s) => s.status === 'published' && !!s.subdomain && !s.subdomain.startsWith('draft-'),
  )
}

/** Whether a card gets the "Terbitkan ke subdomain" button. */
export function canPublishToSubdomain(site: SiteRow, sites: SiteRow[]): boolean {
  return !!site.replaceable_draft && liveTargets(sites).length > 0
}

function norm(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, ' ')
}

/** Pre-select the live site with the same business name, else the first. */
export function defaultTarget(draft: SiteRow, targets: SiteRow[]): SiteRow | null {
  if (targets.length === 0) return null
  return targets.find((t) => norm(t.business_name) === norm(draft.business_name)) || targets[0]
}

export function targetLabel(target: SiteRow): string {
  return `${siteHost(target.subdomain || '', target.site_domain)} — ${target.business_name}`
}

/** The request body for the replace publish. */
export function replacePublishBody(draftId: string, targetId: string): { draft_id: string; replace_website_id: string } {
  return { draft_id: draftId, replace_website_id: targetId }
}

/** The warning shown before the swap. */
export function replaceWarning(draft: SiteRow, target: SiteRow): string {
  return (
    `Halaman langsung di ${siteHost(target.subdomain || '', target.site_domain)} akan digantikan dengan draf ` +
    `"${draft.business_name}". Halaman lama tidak boleh dipulihkan selepas ini.`
  )
}

/** Merchant-facing message for a refused or failed publish. */
export function replaceErrorMessage(status: number, body: { error?: string; message?: string } | null): string {
  if (body?.error === 'email_not_verified') return 'Sila sahkan e-mel anda sebelum menerbitkan.'
  if (body?.message) return body.message
  if (status === 401) return 'Sesi tamat. Sila log masuk semula.'
  return 'Gagal menerbitkan. Sila cuba lagi.'
}

/** Drafts the merchant can publish now (listed first by the API). */
export function publishableDrafts(sites: SiteRow[]): SiteRow[] {
  return sites.filter((s) => canPublishToSubdomain(s, sites))
}

/** The query that opens the publish dialog on My Projects. */
export function publishLink(draftId: string): string {
  return `/my-projects?publish=${encodeURIComponent(draftId)}`
}

/** The draft named by ?publish=<id>, when it can be published. */
export function draftFromQuery(search: string, sites: SiteRow[]): SiteRow | null {
  const id = new URLSearchParams(search).get('publish')
  if (!id) return null
  const draft = sites.find((s) => s.id === id)
  return draft && canPublishToSubdomain(draft, sites) ? draft : null
}

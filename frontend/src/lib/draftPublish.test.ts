import { describe, expect, it } from 'vitest'
import {
  canPublishToSubdomain,
  defaultTarget,
  draftFromQuery,
  publishLink,
  publishableDrafts,
  liveTargets,
  replaceErrorMessage,
  replacePublishBody,
  replaceWarning,
  targetLabel,
  type SiteRow,
} from './draftPublish'

const live: SiteRow = { id: '3103bded', business_name: 'Ayam Gepuk Panglima', subdomain: 'agp', status: 'published' }
const other: SiteRow = { id: 'x2', business_name: 'Kedai Kuih', subdomain: 'kuih', status: 'published' }
const draft: SiteRow = { id: 'a1df9b79', business_name: 'Ayam Gepuk Panglima', subdomain: null, status: 'draft', replaceable_draft: true }
const plainDraft: SiteRow = { id: 'd3', business_name: 'Draf lama', subdomain: null, status: 'draft' }

describe('draftPublish', () => {
  it('lists only published sites with a real subdomain as targets', () => {
    const sites = [live, other, draft, { ...plainDraft, subdomain: 'draft-d3', status: 'published' }]
    expect(liveTargets(sites).map((s) => s.id)).toEqual(['3103bded', 'x2'])
  })

  it('shows the button only on a replaceable draft when a live site exists', () => {
    expect(canPublishToSubdomain(draft, [live, draft])).toBe(true)
    expect(canPublishToSubdomain(plainDraft, [live, plainDraft])).toBe(false)
    expect(canPublishToSubdomain(draft, [draft])).toBe(false)
    expect(canPublishToSubdomain(live, [live])).toBe(false)
  })

  it('pre-selects the live site with the same business name', () => {
    expect(defaultTarget(draft, [other, live])?.id).toBe('3103bded')
    expect(defaultTarget({ ...draft, business_name: 'Lain' }, [other, live])?.id).toBe('x2')
    expect(defaultTarget(draft, [])).toBeNull()
  })

  it('sends only the two ids and warns in Malay', () => {
    expect(replacePublishBody('a1df9b79', '3103bded')).toEqual({ draft_id: 'a1df9b79', replace_website_id: '3103bded' })
    expect(targetLabel(live)).toBe('agp.binaapp.my — Ayam Gepuk Panglima')
    expect(replaceWarning(draft, live)).toBe(
      'Halaman langsung di agp.binaapp.my akan digantikan dengan draf "Ayam Gepuk Panglima". Halaman lama tidak boleh dipulihkan selepas ini.',
    )
  })

  it('turns refusals into merchant messages', () => {
    expect(replaceErrorMessage(403, { error: 'email_not_verified' })).toBe('Sila sahkan e-mel anda sebelum menerbitkan.')
    expect(replaceErrorMessage(403, { error: 'replace_not_owner', message: 'Draf dan laman langsung mesti milik akaun anda.' }))
      .toBe('Draf dan laman langsung mesti milik akaun anda.')
    expect(replaceErrorMessage(401, null)).toBe('Sesi tamat. Sila log masuk semula.')
    expect(replaceErrorMessage(500, null)).toBe('Gagal menerbitkan. Sila cuba lagi.')
  })

  it('links the dashboard banner to the publish dialog for that draft', () => {
    const sites = [draft, live, plainDraft]
    expect(publishableDrafts(sites).map((s) => s.id)).toEqual(['a1df9b79'])
    expect(publishLink('a1df9b79')).toBe('/my-projects?publish=a1df9b79')
    expect(draftFromQuery('?publish=a1df9b79', sites)?.id).toBe('a1df9b79')
    expect(draftFromQuery('?publish=d3', sites)).toBeNull()
    expect(draftFromQuery('?publish=a1df9b79', [draft])).toBeNull() // no live site to replace
    expect(draftFromQuery('', sites)).toBeNull()
  })
})

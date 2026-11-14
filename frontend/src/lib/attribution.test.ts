import { describe, it, expect } from 'vitest'

import { buildAttribution, dayKey, externalReferrer, hasCampaignSignal } from './attribution'

describe('externalReferrer', () => {
  it('keeps an outside host and strips www', () => {
    expect(externalReferrer('https://www.tiktok.com/@binaapp.my/video/1')).toBe('tiktok.com')
  })

  it('ignores our own site, empty values and junk', () => {
    expect(externalReferrer('https://binaapp.my/login')).toBeUndefined()
    expect(externalReferrer('https://www.binaapp.my/')).toBeUndefined()
    expect(externalReferrer('https://kedai.binaapp.my/')).toBeUndefined()
    expect(externalReferrer('')).toBeUndefined()
    expect(externalReferrer('not a url')).toBeUndefined()
  })
})

describe('buildAttribution', () => {
  const now = new Date('2026-11-14T03:00:00Z')

  it('reads utm tags, referral code, referrer and landing path', () => {
    const a = buildAttribution(
      '?utm_source=tiktok&utm_medium=video&utm_campaign=warung-demo&utm_content=v3&ref=ALI123',
      'https://www.tiktok.com/',
      '/',
      now
    )
    expect(a).toEqual({
      utm_source: 'tiktok',
      utm_medium: 'video',
      utm_campaign: 'warung-demo',
      utm_content: 'v3',
      ref: 'ALI123',
      referrer: 'tiktok.com',
      landing_path: '/',
      first_seen: '2026-11-14T03:00:00.000Z',
    })
  })

  it('omits empty fields for a direct visit', () => {
    const a = buildAttribution('', '', '/register', now)
    expect(a).toEqual({ landing_path: '/register', first_seen: '2026-11-14T03:00:00.000Z' })
    expect(hasCampaignSignal(a)).toBe(false)
  })

  it('clips oversized values', () => {
    const a = buildAttribution(`?utm_source=${'x'.repeat(500)}`, '', '/', now)
    expect(a.utm_source).toHaveLength(200)
  })

  it('treats a referrer alone as a campaign signal', () => {
    expect(hasCampaignSignal(buildAttribution('', 'https://google.com/', '/', now))).toBe(true)
  })
})

describe('dayKey', () => {
  it('formats a local calendar day', () => {
    expect(dayKey(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05')
  })
})

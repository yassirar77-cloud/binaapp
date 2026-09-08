import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/supabase', () => ({
  supabase: null,
  getApiAuthToken: vi.fn(async () => 'token-123'),
}))

import { checkCreateWebsiteAllowed } from './quota'

const jsonResponse = (body: unknown, ok = true) =>
  ({ ok, json: async () => body }) as Response

describe('checkCreateWebsiteAllowed', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('surfaces plan limit + purchased slots as totalAllowed', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({
        allowed: false,
        current_usage: 3,
        limit: 1,
        total_allowed: 3,
        can_buy_addon: true,
        addon_type: 'website',
        addon_price: 5,
      }),
    )

    const res = await checkCreateWebsiteAllowed()

    expect(res.allowed).toBe(false)
    expect(res.currentUsage).toBe(3)
    expect(res.limit).toBe(1)
    // The modal shows totalAllowed so a full account reads "3/3", not "3/1".
    expect(res.totalAllowed).toBe(3)
    expect(res.canBuyAddon).toBe(true)
    expect(res.addonPrice).toBe(5)
    expect(res.unlimited).toBe(false)
  })

  it('falls back to the plan limit when the backend omits total_allowed', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ allowed: true, current_usage: 0, limit: 1, remaining: 1 }),
    )

    const res = await checkCreateWebsiteAllowed()

    expect(res.allowed).toBe(true)
    expect(res.totalAllowed).toBe(1)
  })

  it('reports unlimited plans with null capacity', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ allowed: true, current_usage: 12, limit: null, unlimited: true }),
    )

    const res = await checkCreateWebsiteAllowed()

    expect(res.unlimited).toBe(true)
    expect(res.limit).toBeNull()
    expect(res.totalAllowed).toBeNull()
  })

  it('fails open on transport errors', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('network down'))

    const res = await checkCreateWebsiteAllowed()

    expect(res.allowed).toBe(true)
    expect(res.unlimited).toBe(true)
    expect(res.totalAllowed).toBeNull()
  })
})

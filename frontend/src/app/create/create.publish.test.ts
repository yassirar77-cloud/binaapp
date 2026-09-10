/**
 * Source-level regression test for the id the /create page uses after
 * publishing.
 *
 * Background: the page generates its own uuid and sends it as website_id
 * to /api/publish. When the merchant publishes to a subdomain they
 * already own, the backend UPDATES that existing row and keeps its id —
 * the client's uuid never exists in the database. The page then started
 * the hero video against its own uuid, which was a guaranteed 404: the
 * clip silently never began, and the merchant saw a static hero after
 * being told the video was generating. The response's `website_id` is the
 * id the row actually has; the hero video must be launched against that.
 *
 * Same style as dashboard.routes.test.ts — the publish handler lives in a
 * ~2700-line client component, so pinning the source is the practical way
 * to keep this from regressing through a careless edit.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const createSource = readFileSync(resolve(__dirname, 'page.tsx'), 'utf-8')

describe('/create post-publish hero video target', () => {
  it('takes the website id from the /api/publish response', () => {
    expect(createSource).toMatch(
      /const publishedWebsiteId(?:\s*:\s*string)?\s*=\s*data\.website_id\s*\|\|\s*websiteId/
    )
  })

  it('launches the hero video against the published id, never the client uuid', () => {
    // Scope to the publish handler: from the response being read to the
    // handler's catch. The separate retry path legitimately calls
    // launchHeroVideo(websiteId, …) with a local read from
    // heroVideoWebsiteId.current — which this handler is what sets.
    // 'const data = await response.json()' also opens the earlier
    // subscription-status handler; this line is unique to the publish one.
    const start = createSource.indexOf('const publishedWebsiteUrl = data.url')
    const end = createSource.indexOf('} catch (err', start)
    expect(start).toBeGreaterThan(-1)
    expect(end).toBeGreaterThan(start)
    const publishHandler = createSource.slice(start, end)

    expect(publishHandler).toMatch(/launchHeroVideo\(publishedWebsiteId,/)
    expect(publishHandler).toMatch(/heroVideoWebsiteId\.current\s*=\s*publishedWebsiteId/)
    // The exact regression: the pre-generated id handed straight to the job.
    expect(publishHandler).not.toMatch(/launchHeroVideo\(websiteId,/)
    expect(publishHandler).not.toMatch(/heroVideoWebsiteId\.current\s*=\s*websiteId\b/)
  })
})

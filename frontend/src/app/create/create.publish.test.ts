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

describe('/create hero video uses the merchant\'s own photo', () => {
  // Regression: a merchant uploaded their storefront as the hero and asked
  // for a video. The page never sent the photo, the description field that
  // seeds the video scene was hidden the moment a photo was uploaded, and
  // the copy promised the scene came from that hidden field. Result: a clip
  // of a different restaurant laid over the photo of the merchant's own.

  it('sends the uploaded hero photo as image_url when starting the job', () => {
    const start = createSource.indexOf('const launchHeroVideo = async')
    const end = createSource.indexOf('runHeroVideoJob(', start)
    const bodyEnd = createSource.indexOf('token,', end)
    expect(start).toBeGreaterThan(-1)
    const jobBody = createSource.slice(end, bodyEnd)
    expect(jobBody).toMatch(/image_url:\s*uploadedImages\.hero\s*\|\|\s*undefined/)
  })

  it('keeps the hero description field available when a photo is uploaded', () => {
    // The card must not be gated behind !uploadedImages.hero any more.
    expect(createSource).not.toMatch(/\{!uploadedImages\.hero && \(\s*<div[^>]*data-testid="hero-image-prompt-card"/)
    expect(createSource).toMatch(/data-testid="hero-image-prompt-card"/)
    // And it tells the merchant why it is still there.
    expect(createSource).toContain('Terangkan gambar hero anda')
  })

  it('no longer promises a scene from a field that may be hidden', () => {
    expect(createSource).not.toContain('adegan video diambil daripada &ldquo;Gambar hero yang anda mahu&rdquo;')
    expect(createSource).toContain('adegan video diambil daripada gambar hero anda dan penerangannya di atas')
  })
})

describe('/create makes the hero video WITH the page, not after publish', () => {
  // Every site the merchant checked right after publishing was static for
  // the minutes a post-publish clip took, and read as "again no video".
  // The clip is now prepared the moment generation starts and the publish
  // carries it; if it is still rendering, the publish attaches the site.

  it('starts the prepared clip as soon as the generation job is accepted', () => {
    const start = createSource.indexOf("console.log('✅ Job started:'")
    expect(start).toBeGreaterThan(-1)
    const afterStart = createSource.slice(start, start + 800)
    expect(afterStart).toMatch(/void prepareHeroVideoEarly\(\)/)
  })

  it('prepares with no site and the form\'s own context', () => {
    const start = createSource.indexOf('const prepareHeroVideoEarly = async')
    expect(start).toBeGreaterThan(-1)
    const fn = createSource.slice(start, createSource.indexOf('const followHeroVideoAfterPublish', start))
    expect(fn).toMatch(/runPreparedHeroVideoJob\(/)
    expect(fn).toMatch(/image_url:\s*uploadedImages\.hero\s*\|\|\s*undefined/)
    expect(fn).toMatch(/hero_image_prompt:\s*heroImagePrompt\.trim\(\)\s*\|\|\s*undefined/)
    expect(fn).toMatch(/description:\s*description/)
    // Only when the merchant asked for one and may have one.
    expect(fn).toMatch(/if \(!heroVideoWanted \|\| !heroVideoOptions \|\| !heroVideoAccess\?\.allowed\) return/)
    // A prepare failure never becomes a page error: publish falls back.
    expect(fn).toMatch(/preparedHeroVideoJobId\.current = null/)
    expect(fn).not.toMatch(/toast\.error/)
  })

  it('hands the prepared job to /api/publish', () => {
    const start = createSource.indexOf("fetch(`${API_BASE_URL}/api/publish`")
    const end = createSource.indexOf('if (!response.ok)', start)
    expect(start).toBeGreaterThan(-1)
    const request = createSource.slice(start, end)
    expect(request).toMatch(/hero_video_job_id:\s*preparedHeroVideoJobId\.current\s*\|\|\s*undefined/)
  })

  it('acts on what the publish did with it, and only starts a fresh job when there was nothing to claim', () => {
    const start = createSource.indexOf('const publishedWebsiteUrl = data.url')
    const end = createSource.indexOf('} catch (err', start)
    const handler = createSource.slice(start, end)
    expect(handler).toMatch(/data\.hero_video/)
    // applied → the page already carries the clip: show it, no job to wait on.
    const applied = handler.indexOf("heroVideoOutcome?.status === 'applied'")
    expect(applied).toBeGreaterThan(-1)
    expect(handler.slice(applied, applied + 900)).toMatch(/setGeneratedHtml\(heroVideoOutcome\.html_content\)/)
    expect(handler.slice(applied, applied + 900)).toMatch(/status:\s*'completed'/)
    // pending → the server applies it when it lands; only watch it.
    const pending = handler.indexOf("heroVideoOutcome?.status === 'pending'")
    expect(pending).toBeGreaterThan(applied)
    expect(handler.slice(pending, pending + 500)).toMatch(/followHeroVideoAfterPublish\(publishedWebsiteId,/)
    // The post-publish job is the fallback, decided AFTER both outcomes.
    const fresh = handler.indexOf('launchHeroVideo(publishedWebsiteId,')
    expect(fresh).toBeGreaterThan(pending)
  })

  it('tells the merchant the clip is being made alongside the page', () => {
    expect(createSource).toContain('data-testid="hero-video-prepared"')
    expect(createSource).toContain('Video latar hero sedia — akan dipasang serentak semasa anda terbitkan.')
    expect(createSource).toContain('Video latar hero sedang dijana bersama laman')
  })

  it('forgets the prepared job when the merchant starts over', () => {
    const resets = createSource.match(/preparedHeroVideoJobId\.current = null/g) || []
    // prepare-failure ×2, publish applied, publish fallback, follow done, two start-over buttons
    expect(resets.length).toBeGreaterThanOrEqual(6)
    expect(createSource).toMatch(/setPublishedUrl\(''\); preparedHeroVideoJobId\.current = null; setHeroVideoJob\(null\); \}\}/)
  })
})

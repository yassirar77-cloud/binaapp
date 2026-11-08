/**
 * Source-level tests for the create-page guards (quality system, stage 4).
 * Same style as create.publish.test.ts: the page is a ~4300-line client
 * component, so pinning the wiring in the source is the practical way to
 * keep a guard from being edited away. The rules themselves are unit
 * tested in lib/createGuards.test.ts.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const src = readFileSync(resolve(__dirname, 'page.tsx'), 'utf-8')

describe('/create guards', () => {
  it('routes a multi-line paste in the name box to the bulk menu parser', () => {
    expect(src).toMatch(/id="cr-business-name"[\s\S]{0,2000}onPaste=\{handleBusinessNamePaste\}/)
    expect(src).toMatch(/const handleBusinessNamePaste[\s\S]{0,400}looksLikeMenuPaste\(text\)[\s\S]{0,200}e\.preventDefault\(\)[\s\S]{0,200}importMenuPasteText\(text\)/)
  })

  it('suggests the subdomain from the business name until the merchant edits it', () => {
    expect(src).toMatch(/useEffect\(\(\) => \{\s*if \(subdomainTouched\) return\s*const suggested = suggestSubdomain\(businessName\)/)
    expect(src).toMatch(/setSubdomainTouched\(true\)\s*setSubdomain\(value\)/)
    // the typo warning stays
    expect(src).toContain('slugMismatchWarning(subdomain, businessName)')
  })

  it('checks subdomain availability against the backend before publish', () => {
    expect(src).toMatch(/const handleCheckAvailability = async \(\) => \{[\s\S]{0,600}\/api\/subdomain\/check\/\$\{encodeURIComponent\(subdomain\)\}/)
    expect(src).toContain("setSubdomainError('Subdomain ni dah ada orang ambik. Cuba yang lain.')")
  })

  it('warns when the hero upload looks like a poster or menu board, with a one-tap move to step 06', () => {
    expect(src).toMatch(/const url = await uploadImageToBackend\(file\)\s*setUploadedImages\(prev => \(\{ \.\.\.prev, hero: url \}\)\)\s*void checkHeroRole\(file, url\)/)
    expect(src).toMatch(/const checkHeroRole = async[\s\S]{0,900}\/api\/image\/role/)
    expect(src).toContain('data-testid="hero-poster-warning"')
    expect(src).toMatch(/onClick=\{moveHeroToMenuBoard\}/)
    expect(src).toMatch(/const moveHeroToMenuBoard = \(\) => \{[\s\S]{0,700}void readMenuFromImage\(idx, url\)/)
  })

  it('blocks Generate for a restaurant with no menu items — no confirm dialog', () => {
    const start = src.indexOf('const handleGenerate = async')
    const body = src.slice(start, start + 6000)
    expect(body).toMatch(/const blocked = generateBlockedReason\(/)
    expect(body).toMatch(/if \(blocked\) \{\s*setError\(blocked\)[\s\S]{0,300}return\s*\}/)
    expect(body).not.toContain('window.confirm')
    expect(src).not.toContain('menuRowsWarning(')
  })

  it('shows the mobile preview (the visual gate screenshot) before the subdomain form', () => {
    expect(src).toMatch(/setGatePreview\(gatePreviewFromStatus\(statusData\)\)/)
    expect(src).toMatch(/: !previewSeen \? 'preview'/)
    expect(src).toContain('data-testid="publish-preview-step"')
    expect(src).toMatch(/gatePreview\?\.url \? \([\s\S]{0,200}<img src=\{gatePreview\.url\}/)
    expect(src).toMatch(/<iframe title="Pratonton telefon" srcDoc=\{generatedHtml\}/)
    expect(src).toContain('data-testid="publish-preview-continue"')
    expect(src).toMatch(/pubState !== 'success' && pubState !== 'publishing' && pubState !== 'preview'/)
    // a new generation resets the preview step
    expect(src).toMatch(/let lastTickAt = startedAt;\s*setGatePreview\(null\);\s*setPreviewSeen\(false\);/)
  })
})

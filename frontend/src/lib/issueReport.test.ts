/**
 * Tests for the Report Issue client logic (lib/issueReport.ts) plus
 * source-string pins for the two flag-gated UI behaviors:
 * - the create flow's AI-image option is the free default (no PREMIUM
 *   gate, sends image_choice 'ai' — never 'none' — when selected), and
 * - the dashboard hides the Report button once the backend 404s.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  ISSUE_CATEGORIES,
  ISSUE_DESCRIPTION_MAX,
  mapReportResponse,
} from './issueReport'

describe('issue categories', () => {
  it('exactly matches the backend category enum', () => {
    expect(ISSUE_CATEGORIES.map((c) => c.id)).toEqual([
      'images_wrong',
      'text_wrong',
      'page_broken',
      'sensitive_content',
      'other',
    ])
  })

  it('every category has a BM label', () => {
    for (const c of ISSUE_CATEGORIES) {
      expect(c.label.length).toBeGreaterThan(0)
    }
  })

  it('description limit matches the backend cap', () => {
    expect(ISSUE_DESCRIPTION_MAX).toBe(500)
  })
})

describe('mapReportResponse', () => {
  it('regen_granted → success outcome with remaining count', () => {
    const out = mapReportResponse(200, {
      status: 'regen_granted',
      regens_remaining: 1,
      report_id: 'rep-1',
    })
    expect(out.kind).toBe('regen_granted')
    if (out.kind === 'regen_granted') {
      expect(out.regensRemaining).toBe(1)
      expect(out.message).toContain('regenerate percuma')
    }
  })

  it('escalated → team-will-review outcome', () => {
    const out = mapReportResponse(200, { status: 'escalated', report_id: 'rep-2' })
    expect(out.kind).toBe('escalated')
    if (out.kind === 'escalated') {
      expect(out.message).toContain('Team kami akan semak')
    }
  })

  it('duplicate flag is surfaced on both success shapes', () => {
    const granted = mapReportResponse(200, {
      status: 'regen_granted',
      regens_remaining: 0,
      duplicate: true,
    })
    expect(granted.kind === 'regen_granted' && granted.duplicate).toBe(true)
    const escalated = mapReportResponse(200, { status: 'escalated', duplicate: true })
    expect(escalated.kind === 'escalated' && escalated.duplicate).toBe(true)
  })

  it('404 → feature_disabled (flag off) so the UI hides the button', () => {
    expect(mapReportResponse(404, { detail: 'Not found' }).kind).toBe('feature_disabled')
  })

  it('429 → rate-limited BM copy', () => {
    const out = mapReportResponse(429, {
      detail: { error: 'rate_limited' },
    })
    expect(out.kind).toBe('error')
    if (out.kind === 'error') {
      expect(out.message).toContain('terlalu banyak kali')
    }
  })

  it('403 → not-authorised BM copy', () => {
    expect(mapReportResponse(403, null).kind).toBe('error')
  })

  it('400 no_completed_generation → friendly not-generated-yet copy', () => {
    const out = mapReportResponse(400, {
      detail: { error: 'no_completed_generation' },
    })
    expect(out.kind).toBe('error')
    if (out.kind === 'error') {
      expect(out.message).toContain('belum siap dijana')
    }
  })

  it('unknown errors → generic friendly error, never a crash', () => {
    expect(mapReportResponse(500, null).kind).toBe('error')
    expect(mapReportResponse(503, undefined).kind).toBe('error')
  })
})

// ── Source pins: create-flow free AI default ────────────────────────────────

const createSource = readFileSync(
  resolve(__dirname, '../app/create/page.tsx'),
  'utf-8',
)

describe('create flow: AI images are the free default', () => {
  it("defaults imageChoice to 'ai'", () => {
    expect(createSource).toMatch(
      /useState<'none' \| 'upload' \| 'ai'>\('ai'\)/,
    )
  })

  it('has no PREMIUM badge or premium flag on the image-source options', () => {
    expect(createSource).not.toContain('PREMIUM')
    expect(createSource).not.toMatch(/premium:\s*true/)
  })

  it('labels the AI option as free with the auto-match subtext', () => {
    expect(createSource).toContain('AI Gambar — Percuma')
    expect(createSource).toContain('Auto-match ikut menu anda')
  })

  it('keeps Tiada gambar and Upload sendiri available', () => {
    expect(createSource).toContain('Tiada gambar')
    expect(createSource).toContain('Upload sendiri')
  })

  it('sends the user selection as image_choice (ai path, not none/quota-0)', () => {
    // The payload uses finalImageChoice which falls back to the user's
    // imageChoice selection — with the 'ai' default and no uploads, the
    // backend receives image_choice='ai' and takes the AI-image path.
    expect(createSource).toContain(
      "const finalImageChoice = allImages.length > 0 ? 'upload' : imageChoice",
    )
    expect(createSource).toContain('image_choice: finalImageChoice')
  })

  it('no longer gates generation on the AI-image quota check', () => {
    // Neither the gate function nor a call to it may exist (an
    // explanatory comment naming it is fine).
    expect(createSource).not.toMatch(/function checkAIImageLimit/)
    expect(createSource).not.toMatch(/checkAIImageLimit\(\)/)
  })
})

// ── Source pins: dashboard Report Issue wiring ──────────────────────────────

const dashboardSource = readFileSync(
  resolve(__dirname, '../app/dashboard/page.tsx'),
  'utf-8',
)

describe('dashboard: Report Issue wiring', () => {
  it('renders the modal and hides buttons when the feature flag is off', () => {
    expect(dashboardSource).toContain('ReportIssueModal')
    // Both layouts (mobile + desktop) pass undefined when disabled.
    const wired = dashboardSource.match(/onReportIssue=\{reportDisabled \? undefined :/g) ?? []
    expect(wired.length).toBe(2)
  })

  it('granted reports route to the regenerate-capable editor', () => {
    expect(dashboardSource).toMatch(/onGoToRegenerate=\{[\s\S]*?\/editor\//)
  })
})

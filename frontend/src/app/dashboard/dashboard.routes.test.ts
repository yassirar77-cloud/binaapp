/**
 * Route-string regression test for the dashboard's edit button.
 *
 * Background: there used to be two editor pages — the legacy
 * /edit/[id] (no description, no regenerate UI) and the new
 * /editor/[id] which PR #665 wired to the regenerate flow. The
 * dashboard's onEdit handlers were pointing at the legacy path, so
 * users never reached the regenerate UI from the dashboard. We've
 * deleted the legacy page and switched the routes; this test pins
 * the routes so the regression can't reappear via a careless edit.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const dashboardSource = readFileSync(
  resolve(__dirname, 'page.tsx'),
  'utf-8'
)

describe('dashboard edit-button routing', () => {
  it('navigates to /editor/[id] (the regenerate-capable editor)', () => {
    // Every onEdit handler in the dashboard must push to /editor/${id}.
    const onEditMatches = dashboardSource.match(/onEdit=\{[^}]+\}/g) ?? []
    expect(onEditMatches.length).toBeGreaterThan(0)
    for (const match of onEditMatches) {
      expect(match).toContain('/editor/')
    }
  })

  it('does not route to the deleted /edit/[id] legacy page', () => {
    // Catches the exact regression we just fixed: router.push(`/edit/${...
    expect(dashboardSource).not.toMatch(/router\.push\(`\/edit\//)
  })
})

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

describe('dashboard website ordering', () => {
  // Publishing to a subdomain the merchant already owns updates that row
  // and keeps its original created_at. Ordered by created_at, a site
  // published a minute ago was filed as months old — buried dozens of
  // cards down and read as "it never saved". Most recently worked-on
  // must come first, with created_at only as the tie-break.
  it('orders by updated_at first, created_at as tie-break', () => {
    const websitesQuery = dashboardSource.match(
      /\.from\('websites'\)[\s\S]*?\.order\('created_at'[^)]*\)/
    )?.[0]
    expect(websitesQuery).toBeDefined()
    const updatedAt = websitesQuery!.indexOf(".order('updated_at', { ascending: false })")
    const createdAt = websitesQuery!.indexOf(".order('created_at', { ascending: false })")
    expect(updatedAt).toBeGreaterThan(-1)
    expect(createdAt).toBeGreaterThan(updatedAt)
  })
})

/**
 * Every dashboard menu link resolves to a real page, and both menus use the
 * one config. (The left drawer's Pesanan → /orders was a 404.) The HTTP
 * check — every link answers 200 on a running site — is
 * scripts/check-nav-links.mjs.
 */
import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { ACCOUNT_NAV_ITEMS, DASHBOARD_NAV_ITEMS } from './dashboardNav'
const { LEGACY_DASHBOARD_ROUTES } = require('../../legacy-routes.js') as { LEGACY_DASHBOARD_ROUTES: Record<string, string> }

const APP = resolve(__dirname, '../app')
const hasPage = (route: string) => existsSync(resolve(APP, '.' + route, 'page.tsx'))
const read = (p: string) => readFileSync(resolve(__dirname, p), 'utf-8')

describe('dashboard nav', () => {
  const all = [...DASHBOARD_NAV_ITEMS, ...ACCOUNT_NAV_ITEMS]

  it.each(all.map((i) => [i.label, i.href]))('%s → %s is a page', (_label, href) => {
    expect(hasPage(href)).toBe(true)
  })

  it('has the account links (Profil, Langganan)', () => {
    expect(ACCOUNT_NAV_ITEMS.map((i) => i.href)).toEqual(['/profile', '/subscription'])
  })

  it.each(['../components/dashboard-new/DashboardHeader.tsx', '../components/dashboard-new/MobileDashboard.tsx'])(
    '%s renders the shared config and no route of its own',
    (file) => {
      const src = read(file)
      expect(src).toContain('DASHBOARD_NAV_ITEMS')
      expect(src).toContain('ACCOUNT_NAV_ITEMS')
      expect(src).toContain('LOGOUT_LABEL')
      for (const old of Object.keys(LEGACY_DASHBOARD_ROUTES)) {
        expect(src).not.toMatch(new RegExp(`href: '${old}'`))
      }
    },
  )

  it.each(Object.entries(LEGACY_DASHBOARD_ROUTES))('old route %s redirects to a page (%s)', (from, to) => {
    expect(hasPage(from)).toBe(false) // a redirect would hide a live page
    expect(hasPage(to)).toBe(true)
  })

  it('next.config.js serves the legacy redirects', () => {
    expect(read('../../next.config.js')).toContain('LEGACY_DASHBOARD_ROUTES')
  })
})

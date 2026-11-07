#!/usr/bin/env node
/**
 * Every dashboard menu link answers 200 — and every old route redirects to
 * a page that does — on a running site.
 *
 *   node scripts/check-nav-links.mjs https://binaapp.my
 *   node scripts/check-nav-links.mjs http://localhost:3000
 *
 * Reads the hrefs from src/lib/dashboardNav.ts and legacy-routes.js, so it
 * checks exactly what the menus render. Exit 1 on any failure.
 */
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const base = (process.argv[2] || 'http://localhost:3000').replace(/\/$/, '')
const navSrc = readFileSync(resolve(root, 'src/lib/dashboardNav.ts'), 'utf-8')
const hrefs = [...navSrc.matchAll(/href: '([^']+)'/g)].map((m) => m[1])
const { LEGACY_DASHBOARD_ROUTES } = createRequire(import.meta.url)(resolve(root, 'legacy-routes.js'))

let failed = 0
async function check(path, expectRedirectTo) {
  const res = await fetch(base + path, { redirect: 'follow', headers: { 'user-agent': 'binaapp-nav-check' } })
  const finalPath = new URL(res.url).pathname
  const ok = res.status === 200 && (!expectRedirectTo || finalPath === expectRedirectTo)
  if (!ok) failed++
  console.log(`${ok ? 'OK  ' : 'FAIL'} ${res.status} ${path}${expectRedirectTo ? ` → ${finalPath}` : ''}`)
}

for (const href of hrefs) await check(href)
for (const [from, to] of Object.entries(LEGACY_DASHBOARD_ROUTES)) await check(from, to)
console.log(failed ? `${failed} link(s) failed` : `all ${hrefs.length + Object.keys(LEGACY_DASHBOARD_ROUTES).length} links OK`)
process.exit(failed ? 1 : 0)

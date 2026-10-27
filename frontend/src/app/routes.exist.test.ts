/**
 * Every static internal link in the frontend must point at a route that
 * exists.
 *
 * Background: a whole family of pages (referrals, notifications, webhooks,
 * sla, trust-score, founder, ai-chat-settings, website-rebuild) sent a
 * signed-out user to `/auth/login`, a route that never existed, so the
 * redirect landed on a 404 instead of the login form. Several "Kembali ke
 * Dashboard" links went to `/profil` (typo of `/profile`) and the usage
 * widget's "Upgrade Plan" button went to `/pricing`, which is not a page.
 * None of these fail type-check, lint, or the build, so this test pins
 * them: it scans the source for `href="/…"`, `router.push('/…')` and
 * `window.location.href = '/…'` string literals and asserts each resolves
 * to a page under src/app, an API route handler, a redirect/rewrite source
 * in next.config.js, or a file in public/.
 *
 * Only static strings are checked. Template literals with `${}` are
 * skipped because their shape cannot be known here.
 */

import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs'
import { join, resolve, relative } from 'node:path'

const FRONTEND_ROOT = resolve(__dirname, '..', '..')
const SRC = join(FRONTEND_ROOT, 'src')
const APP = join(SRC, 'app')
const PUBLIC = join(FRONTEND_ROOT, 'public')

// Sources of the redirects()/rewrites() in next.config.js. Kept in sync by
// hand; the config is CommonJS with async functions so it is cheaper to
// list them than to execute it.
const CONFIG_ALIASES = ['/terms', '/privacy', '/terma', '/privasi', '/daftar', '/backend']

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      if (name === 'node_modules' || name === '.next') continue
      walk(full, out)
    } else if (/\.(tsx?|jsx?)$/.test(name) && !/\.test\.(tsx?|jsx?)$/.test(name)) {
      out.push(full)
    }
  }
  return out
}

/** Route patterns, one per page.tsx / route.ts, as segment arrays. */
function collectRoutes(): string[][] {
  const routes: string[][] = []
  const visit = (dir: string, segments: string[]) => {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name)
      if (statSync(full).isDirectory()) {
        // Route groups "(group)" do not add a URL segment.
        const next = /^\(.*\)$/.test(name) ? segments : [...segments, name]
        visit(full, next)
      } else if (/^(page|route)\.(tsx?|jsx?)$/.test(name)) {
        routes.push(segments)
      }
    }
  }
  visit(APP, [])
  return routes
}

function matchesRoute(path: string, routes: string[][]): boolean {
  const parts = path.split('/').filter(Boolean)
  return routes.some((pattern) => {
    // Catch-all "[...slug]" matches the rest.
    const catchAll = pattern.findIndex((s) => /^\[\.\.\./.test(s))
    if (catchAll !== -1) {
      if (parts.length < catchAll) return false
      return pattern.slice(0, catchAll).every((seg, i) => segMatches(seg, parts[i]))
    }
    if (pattern.length !== parts.length) return false
    return pattern.every((seg, i) => segMatches(seg, parts[i]))
  })
}

function segMatches(pattern: string, actual: string): boolean {
  if (/^\[.*\]$/.test(pattern)) return actual.length > 0
  return pattern === actual
}

function isPublicFile(path: string): boolean {
  return existsSync(join(PUBLIC, path))
}

const LINK_RE =
  /(?:href=\{?|router\.(?:push|replace)\(|window\.location\.href\s*=\s*|redirect\()\s*(["'`])(\/[^"'`\s]*)\1/g

describe('internal links resolve to real routes', () => {
  const routes = collectRoutes()
  const files = walk(SRC)

  const broken: string[] = []
  const seen = new Set<string>()

  for (const file of files) {
    const source = readFileSync(file, 'utf-8')
    let m: RegExpExecArray | null
    LINK_RE.lastIndex = 0
    while ((m = LINK_RE.exec(source)) !== null) {
      const raw = m[2]
      if (raw.includes('${')) continue // dynamic, cannot be checked statically
      const path = raw.replace(/[?#].*$/, '').replace(/\/+$/, '') || '/'
      if (path.startsWith('//')) continue // protocol-relative external URL
      const key = `${path}`
      if (seen.has(key)) continue
      seen.add(key)

      const ok =
        matchesRoute(path, routes) ||
        CONFIG_ALIASES.some((a) => path === a || path.startsWith(a + '/')) ||
        isPublicFile(path)
      if (!ok) {
        broken.push(`${relative(FRONTEND_ROOT, file)} → ${raw}`)
      }
    }
  }

  it('finds at least one page route (sanity)', () => {
    expect(routes.length).toBeGreaterThan(10)
    expect(matchesRoute('/login', routes)).toBe(true)
    expect(matchesRoute('/editor/abc', routes)).toBe(true)
  })

  it('has no link to a route that does not exist', () => {
    expect(broken, `Dead internal links:\n${broken.join('\n')}`).toEqual([])
  })

  it('rejects the known dead targets by name', () => {
    // The exact regressions this test was written for.
    for (const dead of ['/auth/login', '/profil', '/pricing', '/edit/abc']) {
      expect(matchesRoute(dead, routes), dead).toBe(false)
    }
  })
})

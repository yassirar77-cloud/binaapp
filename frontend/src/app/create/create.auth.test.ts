/**
 * /api/generate/start and /api/generate/refine take the merchant from the
 * Bearer token (the backend ignores the body's user_id/email). If the page
 * stops sending the token, every generation answers 401 — pin it.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const src = readFileSync(resolve(__dirname, 'page.tsx'), 'utf-8')

describe('/create sends the auth token to generation', () => {
  it('start: token required, sent as Bearer', () => {
    expect(src).toMatch(/const startToken = \(await getApiAuthToken\(\)\) \|\| getStoredToken\(\)/)
    expect(src).toMatch(/if \(!startToken\) \{\s*setError\('Sila log masuk semula untuk menjana website\.'\)/)
    expect(src).toMatch(/api\/generate\/start`, \{\s*method: 'POST',\s*headers: \{ 'Content-Type': 'application\/json', Authorization: `Bearer \$\{startToken\}` \}/)
  })

  it('refine: sent as Bearer', () => {
    expect(src).toMatch(/api\/generate\/refine`, \{\s*method: 'POST',\s*headers: \{ 'Content-Type': 'application\/json', \.\.\.\(refineToken \? \{ Authorization: `Bearer \$\{refineToken\}` \} : \{\}\) \}/)
  })

  it('shows the 401 and 429 messages instead of a generic failure', () => {
    expect(src).toMatch(/startResponse\.status === 401 \|\| errorData\.error === 'auth_required'/)
    expect(src).toMatch(/startResponse\.status === 429 && \(errorData\.error === 'rate_limited' \|\| errorData\.error === 'too_many_running'\)/)
  })
})

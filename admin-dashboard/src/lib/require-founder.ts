import { NextRequest, NextResponse } from 'next/server'
import { API_BASE, FOUNDER_EMAIL } from './founder'

/**
 * Server-side guard for /api/* routes.
 *
 * Reads `Authorization: Bearer <token>`, asks the backend (`GET /api/v1/me`,
 * which validates the JWT) who the token belongs to, and only lets the founder
 * through. Returns a 401 NextResponse to send back, or null when allowed.
 */
export async function requireFounder(request: NextRequest): Promise<NextResponse | null> {
  const header = request.headers.get('authorization') || ''
  const token = header.startsWith('Bearer ') ? header.slice(7).trim() : ''

  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    if (!res.ok) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const me = await res.json()
    if (typeof me?.email !== 'string' || me.email.toLowerCase() !== FOUNDER_EMAIL.toLowerCase()) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 401 })
    }
    return null
  } catch (err) {
    console.error('[Auth] token verification failed:', err)
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
}

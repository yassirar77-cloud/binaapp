import { NextResponse } from 'next/server'
import { FOUNDER_EMAIL } from './supabase'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

/**
 * Server-side check that the caller is the founder.
 *
 * The admin login stores the backend's access token in the browser. Routes
 * that return private customer data (emails, phone numbers) send it as
 * `Authorization: Bearer <token>`; here the backend says whose token it is.
 * Returns a 401 response to send back, or null when the caller may proceed.
 */
export async function requireFounder(request: Request): Promise<NextResponse | null> {
  const header = request.headers.get('authorization') || ''
  const token = header.toLowerCase().startsWith('bearer ') ? header.slice(7).trim() : ''
  if (!token) {
    return NextResponse.json({ error: 'Sign in again to view this.' }, { status: 401 })
  }
  try {
    const res = await fetch(`${API_BASE}/api/v1/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    if (res.ok) {
      const me = await res.json()
      if (String(me?.email || '').toLowerCase() === FOUNDER_EMAIL.toLowerCase()) return null
    }
  } catch (err) {
    console.error('[requireFounder] backend check failed:', err)
    return NextResponse.json({ error: 'Could not verify your sign-in. Try again.' }, { status: 503 })
  }
  return NextResponse.json({ error: 'Sign in again to view this.' }, { status: 401 })
}

/** The stored admin token, for fetches from the browser. */
export function authHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {}
  try {
    const token = localStorage.getItem('binaapp_admin_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {}
  }
}

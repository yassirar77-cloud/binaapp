'use client'

import { TOKEN_KEY, USER_KEY } from './founder'

/**
 * fetch() wrapper for the dashboard's own /api/* routes: attaches the stored
 * admin token as a Bearer header. On 401 the stored session is cleared and the
 * page reloads to the login screen.
 */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  let token = ''
  try {
    token = localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    // storage unavailable
  }

  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(input, { ...init, headers })

  if (res.status === 401) {
    try {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    } catch {
      // ignore
    }
    window.location.reload()
  }

  return res
}

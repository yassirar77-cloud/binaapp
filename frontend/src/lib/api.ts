import { supabase, getStoredToken } from './supabase'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  'https://binaapp-backend.onrender.com'

/**
 * Get current auth token
 * CRITICAL: Mobile browsers block cross-domain cookies, so we MUST
 * send JWT token in Authorization header for all API requests
 *
 * Priority:
 * 1. Backend token stored in localStorage (from our /api/v1/login or /api/v1/register)
 * 2. Supabase session token (fallback for OAuth or email confirmation flows)
 */
async function getAuthToken(): Promise<string | null> {
  // First, check for our backend token
  const backendToken = getStoredToken()
  if (backendToken) {
    return backendToken
  }

  // Fallback to Supabase session
  if (!supabase) return null

  try {
    const { data: { session }, error } = await supabase.auth.getSession()

    if (error) {
      console.error('[API] Error getting session:', error)
      return null
    }

    if (session?.access_token) {
      return session.access_token
    }

    // Try to refresh if no session
    const { data: refreshData } = await supabase.auth.refreshSession()
    return refreshData.session?.access_token || null
  } catch (err) {
    console.error('[API] Error getting auth token:', err)
    return null
  }
}

export async function apiFetch(
  path: string,
  options?: RequestInit & { timeout?: number; skipAuth?: boolean }
) {
  // Default timeout: 2 minutes for mobile compatibility
  const timeout = options?.timeout || 120000
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const extraHeaders = (options?.headers || {}) as Record<string, string>

    // CRITICAL FIX: Get JWT token and add to Authorization header
    // This works on mobile browsers where cookies are blocked
    if (!options?.skipAuth) {
      const token = await getAuthToken()
      if (token) {
        // DEBUG: Log token info (first 20 chars only for security)
        console.log('[API] 🔍 Token being sent:', token.substring(0, 20) + '...')
        console.log('[API] 🔍 Token length:', token.length)

        // Validate token is not a literal string "undefined" or "null"
        if (token === 'undefined' || token === 'null' || token === 'None') {
          console.error('[API] ❌ Invalid token value detected:', token)
        } else {
          extraHeaders['Authorization'] = `Bearer ${token}`
          console.log('[API] ✅ Added Authorization header for:', path)
        }
      } else {
        console.warn('[API] ⚠️ No auth token available for:', path)
      }
    }

    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...extraHeaders,
      },
      ...{ ...options, headers: undefined },
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!res.ok) {
      const text = await res.text()
      console.error('[API] Request failed:', res.status, text)
      throw new Error(text || 'API request failed')
    }

    return res.json()
  } catch (error: any) {
    clearTimeout(timeoutId)

    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please check your connection and try again.')
    }

    throw error
  }
}

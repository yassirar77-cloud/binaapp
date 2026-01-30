import {
  supabase,
  getStoredToken,
  ensureValidToken,
  refreshToken,
  clearAuthData,
  isTokenExpired
} from './supabase'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  'https://binaapp-backend.onrender.com'

// Track if we're currently handling a 401 redirect to prevent loops
let isRedirectingToLogin = false

/**
 * Get current auth token
 * CRITICAL: Mobile browsers block cross-domain cookies, so we MUST
 * send JWT token in Authorization header for all API requests
 *
 * Priority:
 * 1. Backend token stored in localStorage (from our /api/v1/login or /api/v1/register)
 *    - Automatically refreshes token if expiring soon
 * 2. Supabase session token (fallback for OAuth or email confirmation flows)
 */
async function getAuthToken(): Promise<string | null> {
  // First, check for our backend token with automatic refresh
  const validToken = await ensureValidToken()
  if (validToken) {
    return validToken
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

/**
 * Handle 401 Unauthorized error
 * Attempts token refresh and returns new token, or redirects to login
 */
async function handle401Error(): Promise<string | null> {
  console.log('[API] Handling 401 error - attempting token refresh...')

  // Try refreshing the token
  const newToken = await refreshToken()

  if (newToken) {
    console.log('[API] Token refreshed successfully after 401')
    return newToken
  }

  // Token refresh failed - redirect to login
  console.log('[API] Token refresh failed - session expired')

  if (!isRedirectingToLogin && typeof window !== 'undefined') {
    isRedirectingToLogin = true
    clearAuthData()

    // Preserve current path for redirect after login
    const currentPath = window.location.pathname + window.location.search
    const loginUrl = `/login?error=session_expired&redirect=${encodeURIComponent(currentPath)}`

    // Show user-friendly message before redirect
    console.log('[API] Redirecting to login...')

    // Small delay to allow any pending operations to complete
    setTimeout(() => {
      window.location.href = loginUrl
      isRedirectingToLogin = false
    }, 100)
  }

  return null
}

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  status: number
  isAuthError: boolean

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.isAuthError = status === 401
  }
}

export async function apiFetch(
  path: string,
  options?: RequestInit & { timeout?: number; skipAuth?: boolean; _isRetry?: boolean }
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
        extraHeaders['Authorization'] = `Bearer ${token}`
        console.log('[API] Added Authorization header for:', path)
      } else {
        console.warn('[API] No auth token available for:', path)
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

    // Handle 401 Unauthorized - attempt token refresh and retry
    if (res.status === 401 && !options?._isRetry && !options?.skipAuth) {
      console.log('[API] Received 401 for:', path, '- attempting recovery...')

      const newToken = await handle401Error()

      if (newToken) {
        // Retry the request with the new token
        console.log('[API] Retrying request with new token:', path)
        return apiFetch(path, { ...options, _isRetry: true })
      }

      // Token refresh failed - throw specific error
      const errorData = await res.json().catch(() => ({ detail: 'Session expired' }))
      throw new ApiError(
        errorData.detail || 'Your session has expired. Please log in again.',
        401
      )
    }

    if (!res.ok) {
      const text = await res.text()
      console.error('[API] Request failed:', res.status, text)

      // Parse error message from JSON response
      let errorMessage = 'API request failed'
      try {
        const errorData = JSON.parse(text)
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch {
        errorMessage = text || errorMessage
      }

      throw new ApiError(errorMessage, res.status)
    }

    return res.json()
  } catch (error: any) {
    clearTimeout(timeoutId)

    if (error.name === 'AbortError') {
      throw new ApiError('Request timed out. Please check your connection and try again.', 408)
    }

    // Re-throw ApiError as-is
    if (error instanceof ApiError) {
      throw error
    }

    throw error
  }
}

/**
 * Helper function to check if user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  const token = await getAuthToken()
  return !!token
}

/**
 * Helper function to get current session status
 */
export function getSessionStatus(): {
  hasToken: boolean
  isExpired: boolean
} {
  const token = getStoredToken()
  return {
    hasToken: !!token,
    isExpired: token ? isTokenExpired() : true
  }
}

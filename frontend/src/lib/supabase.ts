import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

// Backend API URL for auth operations
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  'https://binaapp-backend.onrender.com'

// Token storage key
const TOKEN_KEY = 'binaapp_auth_token'
const USER_KEY = 'binaapp_user'
const TOKEN_EXPIRY_KEY = 'binaapp_token_expiry'

// Token refresh threshold (5 minutes before expiry)
const TOKEN_REFRESH_THRESHOLD_MS = 5 * 60 * 1000

// Singleton promise to prevent concurrent refresh requests
let refreshPromise: Promise<string | null> | null = null

export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey, {
        auth: {
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true,
          storage: typeof window !== 'undefined' ? window.localStorage : undefined,
          // Mobile browser support
          flowType: 'pkce', // Better for mobile browsers
          debug: process.env.NODE_ENV === 'development',
        },
        global: {
          headers: {
            'X-Client-Info': 'binaapp-web',
          },
        },
      })
    : null

/**
 * Get stored auth token from localStorage
 */
export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * Get an auth token usable for backend API calls.
 *
 * Priority:
 * 1) Custom backend JWT stored in localStorage (`binaapp_auth_token`)
 * 2) Supabase session access token (OAuth / magic link)
 */
export async function getApiAuthToken(): Promise<string | null> {
  const customToken = getStoredToken()
  if (customToken) return customToken

  if (typeof window === 'undefined' || !supabase) return null

  try {
    const {
      data: { session },
    } = await supabase.auth.getSession()
    return session?.access_token || null
  } catch {
    return null
  }
}

/**
 * Store auth token in localStorage AND as a cookie (for middleware)
 */
function storeAuthData(token: string, user: any) {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))

  // Also set as cookie so middleware can check auth status
  // Cookie expires in 7 days, matches typical JWT expiration
  const expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toUTCString()
  document.cookie = `${TOKEN_KEY}=${token}; path=/; expires=${expires}; SameSite=Lax`
}

/**
 * Clear stored auth data (localStorage and cookie)
 */
export function clearAuthData() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(TOKEN_EXPIRY_KEY)

  // Also clear the cookie
  document.cookie = `${TOKEN_KEY}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`
}

/**
 * Decode JWT token to extract payload (without verification)
 * Used client-side to check expiration time
 */
function decodeToken(token: string): { exp?: number; sub?: string; email?: string } | null {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return null

    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (e) {
    console.error('[Auth] Failed to decode token:', e)
    return null
  }
}

/**
 * Check if the stored token is expiring soon (within 5 minutes)
 */
export function isTokenExpiringSoon(): boolean {
  if (typeof window === 'undefined') return false

  const token = getStoredToken()
  if (!token) return false

  const payload = decodeToken(token)
  if (!payload?.exp) return false

  const expiresAt = payload.exp * 1000 // Convert to milliseconds
  const now = Date.now()

  return (expiresAt - now) < TOKEN_REFRESH_THRESHOLD_MS
}

/**
 * Check if the stored token has expired
 */
export function isTokenExpired(): boolean {
  if (typeof window === 'undefined') return true

  const token = getStoredToken()
  if (!token) return true

  const payload = decodeToken(token)
  if (!payload?.exp) return true

  const expiresAt = payload.exp * 1000 // Convert to milliseconds
  return Date.now() >= expiresAt
}

/**
 * Get token expiration time in milliseconds
 */
export function getTokenExpiryTime(): number | null {
  if (typeof window === 'undefined') return null

  const token = getStoredToken()
  if (!token) return null

  const payload = decodeToken(token)
  if (!payload?.exp) return null

  return payload.exp * 1000 // Convert to milliseconds
}

/**
 * Refresh the authentication token via backend API
 * Uses singleton pattern to prevent concurrent refresh requests
 */
export async function refreshToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null

  // If there's already a refresh in progress, return that promise
  if (refreshPromise) {
    console.log('[Auth] Token refresh already in progress, waiting...')
    return refreshPromise
  }

  const currentToken = getStoredToken()
  if (!currentToken) {
    console.log('[Auth] No token to refresh')
    return null
  }

  console.log('[Auth] Starting token refresh...')

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentToken}`
        }
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error('[Auth] Token refresh failed:', response.status, errorData)

        // If refresh fails with 401, the token is truly invalid
        if (response.status === 401) {
          clearAuthData()
          return null
        }
        return null
      }

      const data = await response.json()

      if (data.access_token) {
        // Store the new token
        const storedUser = localStorage.getItem(USER_KEY)
        const user = storedUser ? JSON.parse(storedUser) : data.user
        storeAuthData(data.access_token, user)
        console.log('[Auth] Token refreshed successfully')
        return data.access_token
      }

      return null
    } catch (error) {
      console.error('[Auth] Token refresh error:', error)
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

/**
 * Ensure token is valid, refreshing if necessary
 * Returns the valid token or null if authentication failed
 */
export async function ensureValidToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null

  const token = getStoredToken()
  if (!token) return null

  // If token is expired, try to refresh
  if (isTokenExpired()) {
    console.log('[Auth] Token expired, attempting refresh...')
    return await refreshToken()
  }

  // If token is expiring soon, refresh proactively
  if (isTokenExpiringSoon()) {
    console.log('[Auth] Token expiring soon, refreshing proactively...')
    // Fire and forget - return current token but refresh in background
    refreshToken().catch(console.error)
    return token
  }

  return token
}

/**
 * Register a new user via backend API
 */
export async function signUp(
  email: string,
  password: string,
  fullName: string
) {
  const response = await fetch(`${API_BASE}/api/v1/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
    }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Gagal mendaftar akaun')
  }

  // Store the token and user data
  storeAuthData(data.access_token, data.user)

  return data
}

/**
 * Sign in a user via backend API
 */
export async function signIn(email: string, password: string) {
  const response = await fetch(`${API_BASE}/api/v1/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
    }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Gagal log masuk')
  }

  // Store the token and user data
  storeAuthData(data.access_token, data.user)

  return data
}

/**
 * Sign out user - clear stored tokens
 */
export async function signOut() {
  // Clear our stored token
  clearAuthData()

  // Also clear Supabase session if available
  if (supabase) {
    try {
      await supabase.auth.signOut()
    } catch (e) {
      // Ignore errors - we've already cleared local storage
    }
  }
}

/**
 * Get current user from stored data or Supabase session
 */
export async function getCurrentUser() {
  // First check localStorage
  if (typeof window !== 'undefined') {
    const storedUser = localStorage.getItem(USER_KEY)
    if (storedUser) {
      try {
        return JSON.parse(storedUser)
      } catch (e) {
        // Invalid JSON, clear it
        localStorage.removeItem(USER_KEY)
      }
    }
  }

  // Fallback to Supabase session
  if (!supabase) return null
  const { data: { user } } = await supabase.auth.getUser()
  return user
}

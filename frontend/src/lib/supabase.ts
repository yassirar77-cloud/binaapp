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
  const token = localStorage.getItem(TOKEN_KEY)

  // DEBUG: Log token retrieval
  if (token) {
    console.log('[Auth] 🔍 Retrieved token from localStorage:', token.substring(0, 20) + '...')
    console.log('[Auth] 🔍 Token length:', token.length)

    // Check for invalid token values
    if (token === 'undefined' || token === 'null' || token === 'None' || token === '') {
      console.error('[Auth] ❌ Invalid token stored in localStorage:', token)
      // Clear the invalid token
      localStorage.removeItem(TOKEN_KEY)
      return null
    }
  } else {
    console.log('[Auth] ⚠️ No token found in localStorage')
  }

  return token
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

  // DEBUG: Validate token before storing
  if (!token || token === 'undefined' || token === 'null' || token === 'None') {
    console.error('[Auth] ❌ Attempted to store invalid token:', token)
    return
  }

  console.log('[Auth] ✅ Storing token:', token.substring(0, 20) + '...')
  console.log('[Auth] ✅ Token length:', token.length)

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
function clearAuthData() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)

  // Also clear the cookie
  document.cookie = `${TOKEN_KEY}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`
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

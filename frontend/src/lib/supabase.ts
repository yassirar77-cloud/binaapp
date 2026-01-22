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
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * Store auth token in localStorage
 */
function storeAuthData(token: string, user: any) {
  if (typeof window === 'undefined') return
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

/**
 * Clear stored auth data
 */
function clearAuthData() {
  if (typeof window === 'undefined') return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
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

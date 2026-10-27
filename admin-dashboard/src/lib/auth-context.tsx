'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { API_BASE, FOUNDER_EMAIL, TOKEN_KEY, USER_KEY } from './founder'

type UserInfo = {
  email: string
  [key: string]: any
}

type AuthState = {
  user: UserInfo | null
  isFounder: boolean
  loading: boolean
  signIn: (email: string, password: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState>({
  user: null,
  isFounder: false,
  loading: true,
  signIn: async () => ({ error: null }),
  signOut: async () => {},
})

function clearStoredSession() {
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(TOKEN_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const isFounder = user?.email === FOUNDER_EMAIL

  useEffect(() => {
    // Restore session from localStorage, but only trust it after the backend
    // confirms the stored token is still valid for that user.
    let cancelled = false
    const restore = async () => {
      let storedToken: string | null = null
      try {
        storedToken = localStorage.getItem(TOKEN_KEY)
        if (!storedToken || !localStorage.getItem(USER_KEY)) {
          clearStoredSession()
          return
        }
        const res = await fetch(`${API_BASE}/api/v1/me`, {
          headers: { Authorization: `Bearer ${storedToken}` },
        })
        if (!res.ok) {
          clearStoredSession()
          return
        }
        const me = await res.json()
        if (typeof me?.email !== 'string') {
          clearStoredSession()
          return
        }
        const userInfo: UserInfo = { ...me, email: me.email }
        localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
        if (!cancelled) setUser(userInfo)
      } catch {
        // Network error or bad storage: do not trust the stored session
        try { clearStoredSession() } catch { /* ignore */ }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    restore()
    return () => { cancelled = true }
  }, [])

  const signIn = async (email: string, password: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await response.json()
      if (!response.ok) {
        return { error: data.detail || data.error || 'Login failed' }
      }
      if (!data.access_token) {
        return { error: 'Login failed: no token returned' }
      }
      const userInfo = data.user ?? { email }
      localStorage.setItem(TOKEN_KEY, data.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
      setUser(userInfo)
      return { error: null }
    } catch (err: any) {
      return { error: err.message || 'Network error' }
    }
  }

  const signOut = async () => {
    clearStoredSession()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isFounder, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

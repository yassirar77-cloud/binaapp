'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { FOUNDER_EMAIL } from './supabase'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'
const TOKEN_KEY = 'binaapp_admin_token'
const USER_KEY = 'binaapp_admin_user'

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const isFounder = user?.email === FOUNDER_EMAIL

  useEffect(() => {
    // Restore session from localStorage
    try {
      const storedUser = localStorage.getItem(USER_KEY)
      const storedToken = localStorage.getItem(TOKEN_KEY)
      if (storedUser && storedToken) {
        setUser(JSON.parse(storedUser))
      }
    } catch {
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(TOKEN_KEY)
    }
    setLoading(false)
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
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isFounder, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

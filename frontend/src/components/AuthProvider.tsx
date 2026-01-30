'use client'

import { useEffect, useRef } from 'react'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import toast from 'react-hot-toast'
import {
  supabase,
  getStoredToken,
  isTokenExpiringSoon,
  isTokenExpired,
  refreshToken,
  clearAuthData,
  getTokenExpiryTime
} from '@/lib/supabase'

// Refresh check interval (every 2 minutes)
const REFRESH_CHECK_INTERVAL = 2 * 60 * 1000

// Protected paths that require authentication
const PROTECTED_PATHS = ['/profile', '/my-projects', '/create']

/**
 * AuthProvider Component
 *
 * Handles:
 * 1. Session initialization on app load
 * 2. Automatic token refresh before expiry
 * 3. Session expiry notifications
 * 4. Supabase auth state changes
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const hasShownExpiredToast = useRef(false)

  // Handle session expired error from URL params
  useEffect(() => {
    const error = searchParams.get('error')
    if (error === 'session_expired' && !hasShownExpiredToast.current) {
      hasShownExpiredToast.current = true
      toast.error('Sesi anda telah tamat. Sila log masuk semula.', {
        duration: 5000,
        id: 'session-expired'
      })
    }
  }, [searchParams])

  // Set up Supabase auth state listener
  useEffect(() => {
    if (!supabase) return

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('[AuthProvider] Auth state changed:', event)

        if (event === 'SIGNED_OUT') {
          // Clear our custom token when Supabase signs out
          clearAuthData()
        }

        if (event === 'TOKEN_REFRESHED' && session) {
          console.log('[AuthProvider] Supabase token refreshed')
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  // Set up automatic token refresh check
  useEffect(() => {
    const checkAndRefreshToken = async () => {
      const token = getStoredToken()
      if (!token) return

      // Check if token is expiring soon
      if (isTokenExpiringSoon()) {
        console.log('[AuthProvider] Token expiring soon, refreshing...')
        const newToken = await refreshToken()

        if (!newToken) {
          console.log('[AuthProvider] Token refresh failed')
          // Only redirect if on protected path
          const isProtected = PROTECTED_PATHS.some(p => pathname.startsWith(p))
          if (isProtected) {
            clearAuthData()
            router.push(`/login?error=session_expired&redirect=${encodeURIComponent(pathname)}`)
          }
        }
      }
    }

    // Initial check
    checkAndRefreshToken()

    // Set up interval for periodic checks
    refreshIntervalRef.current = setInterval(checkAndRefreshToken, REFRESH_CHECK_INTERVAL)

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
      }
    }
  }, [pathname, router])

  // Log token expiry time on mount (for debugging)
  useEffect(() => {
    const expiryTime = getTokenExpiryTime()
    if (expiryTime) {
      const expiresIn = Math.round((expiryTime - Date.now()) / 1000 / 60)
      console.log(`[AuthProvider] Token expires in ${expiresIn} minutes`)
    }
  }, [])

  return <>{children}</>
}

import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Token key must match the one in supabase.ts
const TOKEN_KEY = 'binaapp_auth_token'

// Founder access cookie key
const FOUNDER_ACCESS_KEY = 'founder_access'

/**
 * Decode JWT token to check expiration (middleware-compatible version)
 * Note: This only checks expiration, not signature validity
 */
function isTokenExpiredInMiddleware(token: string): boolean {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return true

    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(Buffer.from(base64, 'base64').toString('utf-8'))

    if (!payload.exp) return true

    const expiresAt = payload.exp * 1000 // Convert to milliseconds
    return Date.now() >= expiresAt
  } catch {
    return true
  }
}

/**
 * Middleware to handle:
 * 1. Coming Soon page - redirects public visitors to /coming-soon
 * 2. Authentication - protects routes that require login
 * 3. Session expiry - redirects to login with appropriate message
 */
export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  const pathname = req.nextUrl.pathname

  // ============================================
  // COMING SOON LOGIC
  // ============================================

  // Paths that should always be accessible (bypass coming soon)
  const comingSoonBypassPaths = [
    '/coming-soon',
    '/founder-login',
    '/_next',
    '/api',
    '/favicon.ico',
    '/manifest.json',
    '/icons',
  ]

  const isComingSoonBypassPath = comingSoonBypassPaths.some(path =>
    pathname.startsWith(path)
  )

  // Check for founder access cookie
  const hasFounderAccess = req.cookies.get(FOUNDER_ACCESS_KEY)?.value === 'true'

  // Redirect to coming-soon if:
  // - Not a bypass path
  // - Doesn't have founder access
  if (!isComingSoonBypassPath && !hasFounderAccess) {
    const comingSoonUrl = req.nextUrl.clone()
    comingSoonUrl.pathname = '/coming-soon'
    return NextResponse.redirect(comingSoonUrl)
  }

  // ============================================
  // EXISTING AUTH LOGIC (only runs if founder has access)
  // ============================================

  // Check for custom BinaApp token in cookies
  const binaappToken = req.cookies.get(TOKEN_KEY)?.value
  let isTokenExpired = false

  // Check if the token is expired
  if (binaappToken) {
    isTokenExpired = isTokenExpiredInMiddleware(binaappToken)
    if (isTokenExpired) {
      console.log('[Middleware] BinaApp token is expired')
    }
  }

  // Also check Supabase session as fallback
  let supabaseSession = null
  try {
    const supabase = createMiddlewareClient({ req, res })
    const { data: { session } } = await supabase.auth.getSession()
    supabaseSession = session
  } catch (e) {
    // Ignore Supabase errors
  }

  // Valid auth = has non-expired token OR has Supabase session
  const hasValidAuth = (!!binaappToken && !isTokenExpired) || !!supabaseSession

  console.log('[Middleware] Path:', pathname, 'Founder:', hasFounderAccess, 'BinaApp token:', !!binaappToken, 'Token expired:', isTokenExpired, 'Supabase session:', !!supabaseSession)

  // Protected routes that require authentication
  const protectedPaths = ['/profile', '/my-projects', '/create']
  const isProtectedPath = protectedPaths.some(path =>
    pathname.startsWith(path)
  )

  // Redirect to login if accessing protected route without valid auth
  if (isProtectedPath && !hasValidAuth) {
    console.log('[Middleware] No valid auth, redirecting to login/daftar')
    const redirectUrl = req.nextUrl.clone()
    if (pathname.startsWith('/create')) {
      redirectUrl.pathname = '/daftar'
    } else {
      redirectUrl.pathname = '/login'
    }
    redirectUrl.searchParams.set('redirect', pathname)

    // Add session_expired flag if token was present but expired
    if (binaappToken && isTokenExpired) {
      redirectUrl.searchParams.set('error', 'session_expired')
    }

    // Clear the expired token cookie in the response
    if (isTokenExpired) {
      const response = NextResponse.redirect(redirectUrl)
      response.cookies.set(TOKEN_KEY, '', {
        path: '/',
        expires: new Date(0)
      })
      return response
    }

    return NextResponse.redirect(redirectUrl)
  }

  // Redirect to dashboard if accessing login/register with active auth
  const authPaths = ['/login', '/register', '/daftar']
  if (authPaths.includes(pathname) && hasValidAuth) {
    console.log('[Middleware] Already logged in, redirecting to my-projects')
    const redirectUrl = req.nextUrl.clone()
    redirectUrl.pathname = '/my-projects'
    return NextResponse.redirect(redirectUrl)
  }

  return res
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ]
}

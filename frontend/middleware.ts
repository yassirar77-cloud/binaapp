import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Token key must match the one in supabase.ts
const TOKEN_KEY = 'binaapp_auth_token'

// Founder access cookie key
const FOUNDER_ACCESS_KEY = 'founder_access'

/**
 * Middleware to handle:
 * 1. Coming Soon page - redirects public visitors to /coming-soon
 * 2. Authentication - protects routes that require login
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

  // Also check Supabase session as fallback
  let supabaseSession = null
  try {
    const supabase = createMiddlewareClient({ req, res })
    const { data: { session } } = await supabase.auth.getSession()
    supabaseSession = session
  } catch (e) {
    // Ignore Supabase errors
  }

  const hasAuth = !!binaappToken || !!supabaseSession

  console.log('[Middleware] Path:', pathname, 'Founder:', hasFounderAccess, 'BinaApp token:', !!binaappToken, 'Supabase session:', !!supabaseSession)

  // Protected routes that require authentication
  const protectedPaths = ['/profile', '/my-projects', '/create']
  const isProtectedPath = protectedPaths.some(path =>
    pathname.startsWith(path)
  )

  // Redirect to login if accessing protected route without auth
  if (isProtectedPath && !hasAuth) {
    console.log('[Middleware] No auth, redirecting to login/daftar')
    const redirectUrl = req.nextUrl.clone()
    if (pathname.startsWith('/create')) {
      redirectUrl.pathname = '/daftar'
    } else {
      redirectUrl.pathname = '/login'
    }
    redirectUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(redirectUrl)
  }

  // Redirect to dashboard if accessing login/register with active auth
  const authPaths = ['/login', '/register', '/daftar']
  if (authPaths.includes(pathname) && hasAuth) {
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

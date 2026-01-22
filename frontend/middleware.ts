import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Token key must match the one in supabase.ts
const TOKEN_KEY = 'binaapp_auth_token'

/**
 * Middleware to protect routes that require authentication
 * Checks both Supabase session AND custom BinaApp token
 */
export async function middleware(req: NextRequest) {
  const res = NextResponse.next()

  // Check for custom BinaApp token in cookies
  // Note: We need to set this cookie during login for middleware to see it
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

  console.log('[Middleware] Path:', req.nextUrl.pathname, 'BinaApp token:', !!binaappToken, 'Supabase session:', !!supabaseSession)

  // Protected routes that require authentication
  const protectedPaths = ['/profile', '/my-projects', '/create']
  const isProtectedPath = protectedPaths.some(path =>
    req.nextUrl.pathname.startsWith(path)
  )

  // Redirect to login if accessing protected route without auth
  if (isProtectedPath && !hasAuth) {
    console.log('[Middleware] No auth, redirecting to login/daftar')
    const redirectUrl = req.nextUrl.clone()
    if (req.nextUrl.pathname.startsWith('/create')) {
      redirectUrl.pathname = '/daftar'
    } else {
      redirectUrl.pathname = '/login'
    }
    redirectUrl.searchParams.set('redirect', req.nextUrl.pathname)
    return NextResponse.redirect(redirectUrl)
  }

  // Redirect to dashboard if accessing login/register with active auth
  const authPaths = ['/login', '/register', '/daftar']
  if (authPaths.includes(req.nextUrl.pathname) && hasAuth) {
    console.log('[Middleware] Already logged in, redirecting to my-projects')
    const redirectUrl = req.nextUrl.clone()
    redirectUrl.pathname = '/my-projects'
    return NextResponse.redirect(redirectUrl)
  }

  return res
}

export const config = {
  matcher: [
    '/profile/:path*',
    '/my-projects/:path*',
    '/create/:path*',
    '/login',
    '/register',
    '/daftar'
  ]
}

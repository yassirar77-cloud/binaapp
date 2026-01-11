import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Middleware to protect routes that require authentication
 * This runs on the server before the page loads, ensuring reliable auth checks
 * on both desktop and mobile browsers
 */
export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  const supabase = createMiddlewareClient({ req, res })

  // Refresh session if expired
  const {
    data: { session },
  } = await supabase.auth.getSession()

  console.log('[Middleware] Path:', req.nextUrl.pathname, 'Has session:', !!session)

  // Protected routes that require authentication
  const protectedPaths = ['/profile', '/my-projects', '/create']
  const isProtectedPath = protectedPaths.some(path =>
    req.nextUrl.pathname.startsWith(path)
  )

  // Redirect to login if accessing protected route without session
  if (isProtectedPath && !session) {
    console.log('[Middleware] No session, redirecting to login')
    const redirectUrl = req.nextUrl.clone()
    redirectUrl.pathname = '/login'
    redirectUrl.searchParams.set('redirect', req.nextUrl.pathname)
    return NextResponse.redirect(redirectUrl)
  }

  // Redirect to dashboard if accessing login/register with active session
  if ((req.nextUrl.pathname === '/login' || req.nextUrl.pathname === '/register') && session) {
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
    '/register'
  ]
}

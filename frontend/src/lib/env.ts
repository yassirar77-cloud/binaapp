/**
 * Environment configuration
 * API base URL for backend requests
 *
 * Uses Vercel proxy (/backend) in production to fix mobile CORS issues
 * Falls back to direct URL for local development
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8000'  // Local development
    : '/backend'  // Production - use Vercel proxy to bypass mobile CORS
)

/**
 * Direct backend URL for async operations (bypasses Vercel proxy timeout)
 *
 * CRITICAL: For async generation endpoints, we MUST call Render directly
 * to avoid Vercel's 10-second timeout on FREE plan.
 *
 * The /backend proxy times out after 10 seconds, but AI generation takes 30-60 seconds.
 */
export const DIRECT_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL ||
  'https://binaapp-backend.onrender.com'

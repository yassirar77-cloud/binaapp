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

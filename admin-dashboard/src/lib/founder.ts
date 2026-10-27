// Founder email - only this person can access the dashboard.
// Kept dependency-free so both server routes and client code can import it.
export const FOUNDER_EMAIL = 'yassirarafat33@yahoo.com'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

export const TOKEN_KEY = 'binaapp_admin_token'
export const USER_KEY = 'binaapp_admin_user'

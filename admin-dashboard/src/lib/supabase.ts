import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Client-side Supabase (for auth and realtime)
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Founder email - only this person can access the dashboard
export const FOUNDER_EMAIL = 'yassirarafat33@yahoo.com'

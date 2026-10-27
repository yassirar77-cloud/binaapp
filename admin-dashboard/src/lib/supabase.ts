import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Client-side Supabase (for auth and realtime)
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Founder email - only this person can access the dashboard (defined in founder.ts
// so server routes can import it without creating a Supabase client)
export { FOUNDER_EMAIL } from './founder'

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey)
    : null

export async function signUp(
  email: string,
  password: string,
  fullName: string
) {
  if (!supabase) throw new Error('Supabase not ready')

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: { full_name: fullName },
    },
  })

  if (error) throw error
  return data
}

export async function signIn(email: string, password: string) {
  if (!supabase) throw new Error('Supabase not ready')

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) throw error
  return data
}

export async function signOut() {
  if (!supabase) throw new Error('Supabase not ready')
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}

export async function getCurrentUser() {
  if (!supabase) return null
  const { data: { user } } = await supabase.auth.getUser()
  return user
}

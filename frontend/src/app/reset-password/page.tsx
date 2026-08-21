/**
 * Reset Password Page — set a new password after clicking the recovery link
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import toast from 'react-hot-toast'
import AuthLayout from '@/components/auth/AuthLayout'
import AuthLogo from '@/components/auth/AuthLogo'
import AuthInput from '@/components/auth/AuthInput'

export default function ResetPasswordPage() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)
  const [invalid, setInvalid] = useState(false)

  useEffect(() => {
    if (!supabase) {
      setInvalid(true)
      return
    }

    // Supabase fires PASSWORD_RECOVERY once it parses the recovery token from
    // the URL. If a session already exists (token already exchanged), accept that too.
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY' || event === 'SIGNED_IN') {
        setReady(true)
      }
    })

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) setReady(true)
    })

    // If neither the event nor a session arrives within a few seconds, the link is bad.
    const timeout = setTimeout(() => {
      setReady((r) => {
        if (!r) setInvalid(true)
        return r
      })
    }, 4000)

    return () => {
      subscription.unsubscribe()
      clearTimeout(timeout)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!supabase) return

    if (password.length < 8) {
      toast.error('Kata laluan mesti sekurang-kurangnya 8 aksara')
      return
    }

    if (password !== confirmPassword) {
      toast.error('Kata laluan tidak sama')
      return
    }

    setLoading(true)

    try {
      const { error } = await supabase.auth.updateUser({ password })
      if (error) throw error

      // Clear the Supabase recovery session — the app's main session uses a custom backend JWT.
      await supabase.auth.signOut()

      toast.success('Kata laluan berjaya dikemaskini. Sila log masuk semula.')
      router.push('/login')
    } catch (error: any) {
      toast.error(error.message || 'Gagal mengemaskini kata laluan')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      {/* Logo */}
      <div className="text-center mb-8">
        <AuthLogo />
      </div>

      {invalid ? (
        <>
          <h1 className="font-display font-medium text-4xl sm:text-5xl text-carbon-900 tracking-[-0.02em] text-center mb-3">
            Pautan Tidak Sah.
          </h1>
          <p className="font-geist text-base text-carbon-400 text-center mb-8">
            Pautan set semula ini telah tamat tempoh atau sudah digunakan.
          </p>

          <div className="bg-white border border-oat-300 shadow-card-warm rounded-2xl p-6 sm:p-8 space-y-4">
            <Link
              href="/lupa-password"
              className="block w-full text-center font-geist font-semibold text-sm text-white bg-clay-500 px-5 py-3.5 rounded-xl shadow-card-warm hover:bg-clay-600 transition-colors tracking-tight"
            >
              Minta Pautan Baharu
            </Link>
            <p className="font-geist text-sm text-carbon-300 text-center">
              <Link href="/login" className="text-clay-600 hover:text-clay-700 font-medium transition-colors">
                Kembali ke log masuk
              </Link>
            </p>
          </div>
        </>
      ) : (
        <>
          <h1 className="font-display font-medium text-4xl sm:text-5xl text-carbon-900 tracking-[-0.02em] text-center mb-3">
            Set Kata Laluan Baharu.
          </h1>
          <p className="font-geist text-base text-carbon-400 text-center mb-8">
            Pilih kata laluan baharu untuk akaun anda
          </p>

          <div className="bg-white border border-oat-300 shadow-card-warm rounded-2xl p-6 sm:p-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              <AuthInput
                label="Kata Laluan Baharu"
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 aksara"
                autoComplete="new-password"
                required
                helperText="Sekurang-kurangnya 8 aksara"
              />

              <AuthInput
                label="Sahkan Kata Laluan"
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Taip semula kata laluan"
                autoComplete="new-password"
                required
              />

              <button
                type="submit"
                disabled={loading || !ready}
                className="w-full font-geist font-semibold text-sm text-white bg-clay-500 px-5 py-3.5 rounded-xl shadow-card-warm hover:bg-clay-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
              >
                {loading ? 'Mengemaskini...' : ready ? 'Kemaskini Kata Laluan' : 'Memuatkan...'}
              </button>
            </form>
          </div>
        </>
      )}
    </AuthLayout>
  )
}

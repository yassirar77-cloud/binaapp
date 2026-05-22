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
          <h1 className="font-geist font-extrabold text-4xl sm:text-5xl text-white tracking-[-0.045em] text-center mb-3">
            Pautan Tidak Sah.
          </h1>
          <p className="font-geist text-base text-ink-300 text-center mb-8">
            Pautan set semula ini telah tamat tempoh atau sudah digunakan.
          </p>

          <div className="bg-ink-800 border border-white/[.08] rounded-2xl p-6 sm:p-8 space-y-4">
            <Link
              href="/lupa-password"
              className="block w-full text-center font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 transition-colors tracking-tight"
            >
              Minta Pautan Baharu
            </Link>
            <p className="font-geist text-sm text-ink-400 text-center">
              <Link href="/login" className="text-brand-300 hover:text-brand-200 font-medium transition-colors">
                Kembali ke log masuk
              </Link>
            </p>
          </div>
        </>
      ) : (
        <>
          <h1 className="font-geist font-extrabold text-4xl sm:text-5xl text-white tracking-[-0.045em] text-center mb-3">
            Set Kata Laluan Baharu.
          </h1>
          <p className="font-geist text-base text-ink-300 text-center mb-8">
            Pilih kata laluan baharu untuk akaun anda
          </p>

          <div className="bg-ink-800 border border-white/[.08] rounded-2xl p-6 sm:p-8">
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
                className="w-full font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
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

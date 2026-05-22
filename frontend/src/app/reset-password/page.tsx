/**
 * Reset Password (Set Semula Kata Laluan) Page
 *
 * Landing page from the Supabase Auth recovery email.
 *
 * Flow:
 * 1. Supabase recovery link redirects here with a PKCE `code` (or legacy
 *    hash tokens). With `detectSessionInUrl: true` + `flowType: 'pkce'`
 *    the client picks the code up; we also call `exchangeCodeForSession`
 *    defensively when a `code` query param is present.
 * 2. We listen for the `PASSWORD_RECOVERY` event from `onAuthStateChange`
 *    and treat the presence of any session as "token validated".
 * 3. User sets a new password; we call `supabase.auth.updateUser`.
 * 4. Sign the user in via the backend with the new password so the rest
 *    of the app gets the custom backend JWT it expects (see comment in
 *    `lib/supabase.ts`), then redirect to `/dashboard`.
 */

'use client'

import { useEffect, useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase, signIn } from '@/lib/supabase'
import toast from 'react-hot-toast'
import AuthLayout from '@/components/auth/AuthLayout'
import AuthLogo from '@/components/auth/AuthLogo'
import AuthInput from '@/components/auth/AuthInput'

type Status = 'verifying' | 'ready' | 'invalid'

function ResetPasswordPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const [status, setStatus] = useState<Status>('verifying')
  const [email, setEmail] = useState<string | null>(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!supabase) {
      setStatus('invalid')
      return
    }

    let mounted = true

    const markReady = (sessionEmail: string | null) => {
      if (!mounted) return
      setEmail(sessionEmail)
      setStatus('ready')
    }

    const verify = async () => {
      const code = searchParams.get('code')
      const errorDescription = searchParams.get('error_description') || searchParams.get('error')

      if (errorDescription) {
        if (mounted) setStatus('invalid')
        return
      }

      // Existing session (e.g. detectSessionInUrl already handled the URL).
      const { data: existing } = await supabase!.auth.getSession()
      if (existing.session) {
        markReady(existing.session.user?.email ?? null)
        return
      }

      if (code) {
        const { data, error } = await supabase!.auth.exchangeCodeForSession(code)
        if (!error && data.session) {
          markReady(data.session.user?.email ?? null)
          return
        }
      }
    }

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (!mounted) return
      if (event === 'PASSWORD_RECOVERY' || (event === 'SIGNED_IN' && session)) {
        markReady(session?.user?.email ?? null)
      }
    })

    verify()

    // If we still haven't validated after a short grace period, treat the
    // link as invalid/expired rather than leaving the user on a spinner.
    const timeout = setTimeout(() => {
      if (!mounted) return
      setStatus((prev) => (prev === 'verifying' ? 'invalid' : prev))
    }, 4000)

    return () => {
      mounted = false
      clearTimeout(timeout)
      listener.subscription.unsubscribe()
    }
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!supabase) {
      toast.error('Sistem tidak tersedia. Sila cuba sebentar lagi.')
      return
    }

    if (password.length < 8) {
      toast.error('Kata laluan mesti sekurang-kurangnya 8 aksara')
      return
    }
    if (password !== confirmPassword) {
      toast.error('Kata laluan tidak sama')
      return
    }

    setSubmitting(true)
    try {
      const { data: updateData, error: updateError } = await supabase.auth.updateUser({
        password,
      })

      if (updateError) {
        toast.error(updateError.message || 'Gagal set semula kata laluan')
        return
      }

      const userEmail = updateData.user?.email ?? email
      toast.success('Kata laluan berjaya ditukar')

      // Clear the Supabase recovery session before signing in via the
      // backend — we use the custom backend JWT for the rest of the app.
      try {
        await supabase.auth.signOut()
      } catch {
        // best-effort
      }

      if (userEmail) {
        try {
          await signIn(userEmail, password)
          router.push('/dashboard')
          return
        } catch {
          // Fall through to manual login below.
        }
      }

      router.push('/login')
    } catch (err: any) {
      toast.error(err?.message || 'Gagal set semula kata laluan')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <div className="text-center mb-8">
        <AuthLogo />
      </div>

      <h1 className="font-geist font-extrabold text-4xl sm:text-5xl text-white tracking-[-0.045em] text-center mb-3">
        Set Semula Kata Laluan
      </h1>
      <p className="font-geist text-base text-ink-300 text-center mb-8">
        {status === 'ready' && email
          ? `Pilih kata laluan baharu untuk ${email}`
          : 'Pilih kata laluan baharu untuk akaun anda'}
      </p>

      <div className="bg-ink-800 border border-white/[.08] rounded-2xl p-6 sm:p-8">
        {status === 'verifying' && (
          <p className="font-geist text-sm text-ink-300 text-center py-6">
            Mengesahkan pautan...
          </p>
        )}

        {status === 'invalid' && (
          <div className="space-y-5">
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-4">
              <p className="font-geist text-sm text-white mb-1.5">
                Pautan tidak sah atau telah tamat tempoh
              </p>
              <p className="font-geist text-sm text-ink-300">
                Pautan set semula kata laluan hanya sah untuk 1 jam dan boleh
                digunakan sekali sahaja. Sila minta pautan baharu.
              </p>
            </div>
            <Link
              href="/lupa-password"
              className="block w-full text-center font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 transition-colors tracking-tight"
            >
              Minta Pautan Baharu
            </Link>
          </div>
        )}

        {status === 'ready' && (
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
              label="Sahkan Kata Laluan Baharu"
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
              disabled={submitting}
              className="w-full font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
            >
              {submitting ? 'Menyimpan...' : 'Simpan Kata Laluan Baharu'}
            </button>
          </form>
        )}

        <p className="font-geist text-sm text-ink-400 text-center mt-6">
          Kembali ke{' '}
          <Link href="/login" className="text-brand-300 hover:text-brand-200 font-medium transition-colors">
            log masuk
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div />}>
      <ResetPasswordPageContent />
    </Suspense>
  )
}

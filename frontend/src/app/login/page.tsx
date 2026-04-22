/**
 * Login Page
 */

'use client'

import { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { signIn } from '@/lib/supabase'
import toast from 'react-hot-toast'
import AuthLayout from '@/components/auth/AuthLayout'
import AuthLogo from '@/components/auth/AuthLogo'
import AuthInput from '@/components/auth/AuthInput'

function LoginPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectUrl = searchParams.get('redirect')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await signIn(email, password)
      toast.success('Berjaya log masuk!')
      // Redirect to the original page if redirect param exists, otherwise to my-projects
      if (redirectUrl) {
        router.push(redirectUrl)
      } else {
        router.push('/my-projects')
      }
    } catch (error: any) {
      toast.error(error.message || 'Gagal log masuk')
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

      {/* Headline */}
      <h1 className="font-geist font-extrabold text-4xl sm:text-5xl text-white tracking-[-0.045em] text-center mb-3">
        Selamat Kembali.
      </h1>
      <p className="font-geist text-base text-ink-300 text-center mb-8">
        Log masuk untuk urus website anda
      </p>

      {/* Form card */}
      <div className="bg-ink-800 border border-white/[.08] rounded-2xl p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          <AuthInput
            label="E-mel"
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="nama@email.com"
            autoComplete="email"
            required
          />

          <AuthInput
            label="Kata Laluan"
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
          >
            {loading ? 'Memuatkan...' : 'Log Masuk'}
          </button>
        </form>

        <p className="font-geist text-sm text-ink-400 text-center mt-6">
          Belum ada akaun?{' '}
          <Link href="/register" className="text-brand-300 hover:text-brand-200 font-medium transition-colors">
            Daftar percuma
          </Link>
        </p>
      </div>

      {/* Trust line */}
      <div className="flex justify-center gap-6 mt-7 font-geist-mono text-[11px] text-ink-400 tracking-[.06em]">
        <span>✓ PERCUMA UNTUK BERMULA</span>
        <span>✓ AI BINA DALAM 60 SAAT</span>
      </div>
    </AuthLayout>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <LoginPageContent />
    </Suspense>
  )
}

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
        router.push('/dashboard')
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
      <h1 className="font-display font-medium text-4xl sm:text-5xl text-carbon-900 tracking-[-0.02em] text-center mb-3">
        Selamat Kembali.
      </h1>
      <p className="font-geist text-base text-carbon-400 text-center mb-8">
        Log masuk untuk urus website anda
      </p>

      {/* Form card */}
      <div className="bg-white border border-oat-300 shadow-card-warm rounded-2xl p-6 sm:p-8">
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

          <div className="text-right">
            <Link
              href="/lupa-password"
              className="font-geist text-sm text-clay-600 hover:text-clay-700 font-medium transition-colors"
            >
              Lupa kata laluan?
            </Link>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full font-geist font-semibold text-sm text-white bg-clay-500 px-5 py-3.5 rounded-xl shadow-card-warm hover:bg-clay-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
          >
            {loading ? 'Memuatkan...' : 'Log Masuk'}
          </button>
        </form>

        <p className="font-geist text-sm text-carbon-300 text-center mt-6">
          Belum ada akaun?{' '}
          <Link href="/register" className="text-clay-600 hover:text-clay-700 font-medium transition-colors">
            Daftar percuma
          </Link>
        </p>
      </div>

      {/* Trust line */}
      <div className="flex justify-center gap-6 mt-7 font-geist-mono text-[11px] text-carbon-300 tracking-[.06em]">
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

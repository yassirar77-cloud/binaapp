/**
 * Register Page
 */

'use client'

import { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { signUp } from '@/lib/supabase'
import toast from 'react-hot-toast'
import AuthLayout from '@/components/auth/AuthLayout'
import AuthLogo from '@/components/auth/AuthLogo'
import AuthInput from '@/components/auth/AuthInput'

function RegisterPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectUrl = searchParams.get('redirect')
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!agreedToTerms) {
      toast.error('Sila bersetuju dengan Polisi Privasi dan Terma Perkhidmatan')
      return
    }

    if (formData.password !== formData.confirmPassword) {
      toast.error('Kata laluan tidak sama')
      return
    }

    if (formData.password.length < 8) {
      toast.error('Kata laluan mesti sekurang-kurangnya 8 aksara')
      return
    }

    setLoading(true)

    try {
      await signUp(
        formData.email,
        formData.password,
        formData.fullName
      )
      toast.success('Akaun berjaya didaftar!')
      // Redirect to my-projects (which uses custom auth) instead of profile (which uses Supabase auth)
      if (redirectUrl) {
        router.push(redirectUrl)
      } else {
        router.push('/dashboard')
      }
    } catch (error: any) {
      toast.error(error.message || 'Gagal mendaftar akaun')
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
        Mula Bina Sekarang.
      </h1>
      <p className="font-geist text-base text-ink-300 text-center mb-8">
        Cipta akaun — percuma untuk bermula
      </p>

      {/* Form card */}
      <div className="bg-ink-800 border border-white/[.08] rounded-2xl p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          <AuthInput
            label="Nama Penuh"
            id="fullName"
            name="fullName"
            placeholder="cth. Ahmad bin Ismail"
            onChange={handleChange}
            autoComplete="name"
            required
          />

          <AuthInput
            label="E-mel"
            id="email"
            name="email"
            type="email"
            placeholder="nama@email.com"
            onChange={handleChange}
            autoComplete="email"
            required
          />

          <AuthInput
            label="Kata Laluan"
            id="password"
            name="password"
            type="password"
            placeholder="Minimum 8 aksara"
            onChange={handleChange}
            autoComplete="new-password"
            required
            helperText="Sekurang-kurangnya 8 aksara"
          />

          <AuthInput
            label="Sahkan Kata Laluan"
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            placeholder="Taip semula kata laluan"
            onChange={handleChange}
            autoComplete="new-password"
            required
          />

          {/* Privacy & Terms Consent */}
          <div className="space-y-2">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                required
                className="mt-1 w-4 h-4 accent-volt-400 rounded border-white/20 bg-ink-700"
              />
              <span className="font-geist text-sm text-ink-300">
                Saya telah membaca dan bersetuju dengan{' '}
                <a
                  href="/privacy-policy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-300 hover:text-brand-200 transition-colors"
                >
                  Polisi Privasi
                </a>
                {' '}dan{' '}
                <a
                  href="/terms-of-service"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-300 hover:text-brand-200 transition-colors"
                >
                  Terma Perkhidmatan
                </a>
              </span>
            </label>
            <p className="font-geist text-xs text-ink-400 pl-7">
              Dengan mendaftar, anda bersetuju dengan amalan pengumpulan data kami seperti yang diterangkan dalam Polisi Privasi
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
          >
            {loading ? 'Memuatkan...' : 'Daftar Sekarang'}
          </button>
        </form>

        <p className="font-geist text-sm text-ink-400 text-center mt-6">
          Sudah ada akaun?{' '}
          <Link href="/login" className="text-brand-300 hover:text-brand-200 font-medium transition-colors">
            Log masuk
          </Link>
        </p>
      </div>

      {/* Trust line */}
      <div className="flex justify-center gap-6 mt-7 font-geist-mono text-[11px] text-ink-400 tracking-[.06em]">
        <span>✓ PERCUMA UNTUK BERMULA</span>
        <span>✓ TANPA KAD KREDIT</span>
      </div>
    </AuthLayout>
  )
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <RegisterPageContent />
    </Suspense>
  )
}

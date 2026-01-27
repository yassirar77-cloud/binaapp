/**
 * Register Page
 */

'use client'

import { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { signUp } from '@/lib/supabase'
import toast from 'react-hot-toast'
import { Sparkles } from 'lucide-react'

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
        router.push('/my-projects')
      }
    } catch (error: any) {
      toast.error(error.message || 'Gagal mendaftar akaun')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-white px-4 py-12">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 text-2xl font-bold">
            <Sparkles className="w-7 h-7 text-primary-600" />
            <span>BinaApp</span>
          </Link>
          <h1 className="text-3xl font-bold mt-6 mb-2">
            Cipta Akaun Percuma
          </h1>
          <p className="text-gray-600">
            Mula bina website anda sekarang
          </p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              name="fullName"
              placeholder="Nama Penuh"
              className="input"
              onChange={handleChange}
              autoComplete="name"
              required
            />
            <input
              name="email"
              type="email"
              placeholder="Email"
              className="input"
              onChange={handleChange}
              autoComplete="email"
              required
            />
            <input
              name="password"
              type="password"
              placeholder="Kata Laluan"
              className="input"
              onChange={handleChange}
              autoComplete="new-password"
              required
            />
            <input
              name="confirmPassword"
              type="password"
              placeholder="Sahkan Kata Laluan"
              className="input"
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
                  className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">
                  I have read and agree to the{' '}
                  <a
                    href="/privacy-policy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Privacy Policy
                  </a>
                  {' '}and{' '}
                  <a
                    href="/terms-of-service"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Terms of Service
                  </a>
                </span>
              </label>
              <p className="text-xs text-gray-500 pl-7">
                By signing up, you consent to our data collection practices as described in our Privacy Policy
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full"
            >
              {loading ? 'Memuatkan...' : 'Daftar Sekarang'}
            </button>
          </form>

          <p className="text-sm text-center mt-6">
            Sudah ada akaun?{' '}
            <Link href="/login" className="text-primary-600 font-medium">
              Log masuk
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <RegisterPageContent />
    </Suspense>
  )
}

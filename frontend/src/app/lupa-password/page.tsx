/**
 * Forgot Password Page — request a reset email
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import toast from 'react-hot-toast'
import AuthLayout from '@/components/auth/AuthLayout'
import AuthLogo from '@/components/auth/AuthLogo'
import AuthInput from '@/components/auth/AuthInput'

export default function LupaPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!supabase) {
      toast.error('Perkhidmatan tidak tersedia. Sila cuba lagi.')
      return
    }

    setLoading(true)

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      })

      if (error) {
        const status = (error as any).status
        if (status === 429) {
          toast.error('Terlalu banyak permintaan. Sila tunggu beberapa minit sebelum cuba lagi.')
          return
        }
        throw error
      }

      setSent(true)
    } catch (error: any) {
      toast.error(error.message || 'Gagal menghantar e-mel set semula')
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

      {sent ? (
        <>
          {/* Headline */}
          <h1 className="font-display font-medium text-4xl sm:text-5xl text-carbon-900 tracking-[-0.02em] text-center mb-3">
            Semak Inbox Anda.
          </h1>
          <p className="font-geist text-base text-carbon-400 text-center mb-8">
            Kami telah hantar pautan set semula kata laluan ke <span className="text-carbon-900">{email}</span>
          </p>

          {/* Confirmation card */}
          <div className="bg-white border border-oat-300 shadow-card-warm rounded-2xl p-6 sm:p-8 space-y-5">
            <p className="font-geist text-sm text-carbon-400">
              Klik pautan dalam e-mel untuk set kata laluan baharu. Pautan ini sah selama 1 jam.
            </p>
            <p className="font-geist text-sm text-carbon-300">
              Tidak nampak e-mel? Semak folder spam atau cuba lagi dengan e-mel yang betul.
            </p>

            <button
              type="button"
              onClick={() => {
                setSent(false)
                setEmail('')
              }}
              className="w-full font-geist font-semibold text-sm text-white bg-clay-500 px-5 py-3.5 rounded-xl shadow-card-warm hover:bg-clay-600 transition-colors tracking-tight"
            >
              Hantar Semula
            </button>

            <p className="font-geist text-sm text-carbon-300 text-center">
              <Link href="/login" className="text-clay-600 hover:text-clay-700 font-medium transition-colors">
                Kembali ke log masuk
              </Link>
            </p>
          </div>
        </>
      ) : (
        <>
          {/* Headline */}
          <h1 className="font-display font-medium text-4xl sm:text-5xl text-carbon-900 tracking-[-0.02em] text-center mb-3">
            Lupa Kata Laluan?
          </h1>
          <p className="font-geist text-base text-carbon-400 text-center mb-8">
            Masukkan e-mel anda — kami hantar pautan untuk set semula
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

              <button
                type="submit"
                disabled={loading}
                className="w-full font-geist font-semibold text-sm text-white bg-clay-500 px-5 py-3.5 rounded-xl shadow-card-warm hover:bg-clay-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
              >
                {loading ? 'Menghantar...' : 'Hantar Pautan Set Semula'}
              </button>
            </form>

            <p className="font-geist text-sm text-carbon-300 text-center mt-6">
              Ingat kata laluan anda?{' '}
              <Link href="/login" className="text-clay-600 hover:text-clay-700 font-medium transition-colors">
                Log masuk
              </Link>
            </p>
          </div>
        </>
      )}
    </AuthLayout>
  )
}

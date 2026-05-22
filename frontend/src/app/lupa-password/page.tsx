/**
 * Lupa Kata Laluan (Forgot Password) Page
 *
 * Sends a Supabase Auth recovery email. The link in the email lands the
 * user on `/reset-password` where they set a new password.
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
      toast.error('Sistem tidak tersedia. Sila cuba sebentar lagi.')
      return
    }

    setLoading(true)
    try {
      const redirectTo = `${window.location.origin}/reset-password`
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo,
      })

      if (error) {
        // Supabase rate limits with HTTP 429 (1 req / 60s per email).
        if (error.status === 429) {
          toast.error('Terlalu banyak permintaan. Sila tunggu seminit sebelum cuba lagi.')
        } else {
          toast.error(error.message || 'Gagal menghantar e-mel set semula')
        }
        return
      }

      setSent(true)
      toast.success('E-mel set semula telah dihantar')
    } catch (err: any) {
      toast.error(err?.message || 'Gagal menghantar e-mel set semula')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <div className="text-center mb-8">
        <AuthLogo />
      </div>

      <h1 className="font-geist font-extrabold text-4xl sm:text-5xl text-white tracking-[-0.045em] text-center mb-3">
        Lupa Kata Laluan?
      </h1>
      <p className="font-geist text-base text-ink-300 text-center mb-8">
        Masukkan e-mel anda — kami akan hantar pautan untuk set semula
      </p>

      <div className="bg-ink-800 border border-white/[.08] rounded-2xl p-6 sm:p-8">
        {sent ? (
          <div className="space-y-5">
            <div className="rounded-xl bg-volt-400/10 border border-volt-400/20 px-4 py-4">
              <p className="font-geist text-sm text-white mb-1.5">
                Semak e-mel anda
              </p>
              <p className="font-geist text-sm text-ink-300">
                Kami telah hantar pautan set semula ke{' '}
                <span className="text-brand-300 font-medium break-all">{email}</span>.
                Pautan akan tamat dalam 1 jam.
              </p>
            </div>

            <p className="font-geist text-xs text-ink-400 text-center">
              Tidak nampak e-mel? Semak folder Spam atau Junk.
            </p>

            <button
              type="button"
              onClick={() => {
                setSent(false)
                setEmail('')
              }}
              className="w-full font-geist text-sm text-brand-300 hover:text-brand-200 font-medium transition-colors"
            >
              Hantar ke e-mel lain
            </button>
          </div>
        ) : (
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
              helperText="Pautan set semula akan dihantar ke e-mel ini"
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
            >
              {loading ? 'Menghantar...' : 'Hantar Pautan Set Semula'}
            </button>
          </form>
        )}

        <p className="font-geist text-sm text-ink-400 text-center mt-6">
          Ingat semula kata laluan?{' '}
          <Link href="/login" className="text-brand-300 hover:text-brand-200 font-medium transition-colors">
            Log masuk
          </Link>
        </p>
      </div>

      <div className="flex justify-center gap-6 mt-7 font-geist-mono text-[11px] text-ink-400 tracking-[.06em]">
        <span>✓ SELAMAT &amp; ENKRIPSI HUJUNG-KE-HUJUNG</span>
      </div>
    </AuthLayout>
  )
}

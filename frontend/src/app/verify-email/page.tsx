/**
 * Verify Email Page
 *
 * Shown after registration. The account already exists and the user can use
 * the builder, but publishing and payment are blocked until they enter the
 * 6-digit code emailed to them.
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { verifyEmail, resendVerification } from '@/lib/supabase'
import toast from 'react-hot-toast'
import AuthLayout from '@/components/auth/AuthLayout'
import AuthLogo from '@/components/auth/AuthLogo'
import AuthInput from '@/components/auth/AuthInput'

const RESEND_COOLDOWN_SECONDS = 30

function VerifyEmailContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectUrl = searchParams.get('redirect') || '/dashboard'
  const email = searchParams.get('email') || ''

  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()

    const cleaned = code.replace(/\D/g, '')
    if (cleaned.length !== 6) {
      toast.error('Sila masukkan kod 6 digit')
      return
    }

    setLoading(true)
    try {
      await verifyEmail(cleaned)
      toast.success('E-mel berjaya disahkan!')
      router.push(redirectUrl)
    } catch (error: any) {
      toast.error(error.message || 'Kod pengesahan tidak sah')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (cooldown > 0) return
    setResending(true)
    try {
      await resendVerification()
      toast.success('Kod baharu telah dihantar ke e-mel anda')
      setCooldown(RESEND_COOLDOWN_SECONDS)
    } catch (error: any) {
      toast.error(error.message || 'Gagal menghantar kod')
    } finally {
      setResending(false)
    }
  }

  return (
    <AuthLayout>
      <div className="text-center mb-8">
        <AuthLogo />
      </div>

      <h1 className="font-geist font-extrabold text-3xl sm:text-4xl text-white tracking-[-0.045em] text-center mb-3">
        Sahkan E-mel Anda
      </h1>
      <p className="font-geist text-base text-ink-300 text-center mb-8">
        Kami telah menghantar kod 6 digit{email ? ` ke ${email}` : ' ke e-mel anda'}.
        Masukkannya untuk menerbitkan website dan membuat pembayaran.
      </p>

      <div className="bg-ink-800 border border-white/[.08] rounded-2xl p-6 sm:p-8">
        <form onSubmit={handleVerify} className="space-y-5">
          <AuthInput
            label="Kod Pengesahan"
            id="code"
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="cth. 123456"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            required
            helperText="Kod ini tamat tempoh dalam 15 minit"
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full font-geist font-bold text-sm text-ink-950 bg-volt-400 px-5 py-3.5 rounded-xl shadow-[0_0_0_1px_theme(colors.volt.500),0_8px_20px_rgba(199,255,61,.4)] hover:bg-volt-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors tracking-tight"
          >
            {loading ? 'Mengesahkan...' : 'Sahkan E-mel'}
          </button>
        </form>

        <div className="text-center mt-6">
          <button
            type="button"
            onClick={handleResend}
            disabled={resending || cooldown > 0}
            className="font-geist text-sm text-brand-300 hover:text-brand-200 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {cooldown > 0
              ? `Hantar semula kod (${cooldown}s)`
              : resending
              ? 'Menghantar...'
              : 'Tidak menerima kod? Hantar semula'}
          </button>
        </div>
      </div>

      <p className="font-geist text-sm text-ink-400 text-center mt-6">
        Anda boleh terus mencuba pembina laman.{' '}
        <Link href={redirectUrl} className="text-brand-300 hover:text-brand-200 font-medium transition-colors">
          Langkau buat masa ini
        </Link>
      </p>
    </AuthLayout>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <VerifyEmailContent />
    </Suspense>
  )
}

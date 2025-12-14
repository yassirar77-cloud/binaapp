/**
 * Register Page
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { signUp } from '../../../lib/supabase'
import toast from 'react-hot-toast'
import { Sparkles } from 'lucide-react'

export default function RegisterPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [loading, setLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

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
      router.push('/dashboard')
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
              required
            />
            <input
              name="email"
              type="email"
              placeholder="Email"
              className="input"
              onChange={handleChange}
              required
            />
            <input
              name="password"
              type="password"
              placeholder="Kata Laluan"
              className="input"
              onChange={handleChange}
              required
            />
            <input
              name="confirmPassword"
              type="password"
              placeholder="Sahkan Kata Laluan"
              className="input"
              onChange={handleChange}
              required
            />

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

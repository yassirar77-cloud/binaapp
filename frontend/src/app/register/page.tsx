/**
 * Register Page
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { signUp } from '@/lib/supabase'
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
      await signUp(formData.email, formData.password, formData.fullName)
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
          <h1 className="text-3xl font-bold mt-6 mb-2">Cipta Akaun Percuma</h1>
          <p className="text-gray-600">Mula bina website anda sekarang</p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium mb-2">
                Nama Penuh
              </label>
              <input
                id="fullName"
                name="fullName"
                type="text"
                value={formData.fullName}
                onChange={handleChange}
                className="input"
                placeholder="Ahmad Abdullah"
                required
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                className="input"
                placeholder="ahmad@email.com"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                Kata Laluan
              </label>
              <input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                className="input"
                placeholder="••••••••"
                minLength={8}
                required
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium mb-2">
                Sahkan Kata Laluan
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleChange}
                className="input"
                placeholder="••••••••"
                minLength={8}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full"
            >
              {loading ? 'Memuatkan...' : 'Daftar Sekarang'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Sudah ada akaun?{' '}
              <Link href="/login" className="text-primary-600 hover:underline font-medium">
                Log masuk
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

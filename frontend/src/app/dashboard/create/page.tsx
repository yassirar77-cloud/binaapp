/**
 * Website Creation Page
 */

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { ArrowLeft, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/api'

/**
 * Types
 */
type WebsiteGenerationRequest = {
  business_name: string
  description: string
  language: 'ms' | 'en'
  subdomain: string
}

/**
 * Helpers
 */
function slugify(text: string) {
  return text
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

function validateSubdomain(subdomain: string) {
  return /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(subdomain)
}

export default function CreateWebsitePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  const [formData, setFormData] = useState<WebsiteGenerationRequest>({
    business_name: '',
    description: '',
    language: 'ms',
    subdomain: '',
  })

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target

    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))

    if (name === 'business_name') {
      setFormData(prev => ({
        ...prev,
        subdomain: slugify(value),
      }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateSubdomain(formData.subdomain)) {
      toast.error('Subdomain tidak sah')
      return
    }

    setLoading(true)

    try {
      // ✅ CORRECT ENDPOINT (FROM SWAGGER)
      await apiFetch('/api/generate', {
        method: 'POST',
        body: JSON.stringify({
          business_name: formData.business_name,
          description: formData.description,
          language: formData.language,
        }),
      })

      toast.success('Website sedang dijana!')
      router.push('/dashboard')
    } catch (error: any) {
      toast.error(error.message || 'Gagal menjana website')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
            Kembali ke Dashboard
          </Link>
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-2xl">
        <h1 className="text-3xl font-bold mb-6">Cipta Website Baharu</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            name="business_name"
            placeholder="Nama Perniagaan"
            className="input"
            onChange={handleChange}
            required
          />

          <textarea
            name="description"
            placeholder="Terangkan perniagaan anda"
            className="input min-h-32"
            onChange={handleChange}
            required
          />

          <input
            name="subdomain"
            placeholder="subdomain"
            className="input"
            value={formData.subdomain}
            onChange={handleChange}
            required
          />

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full"
          >
            {loading ? 'Menjana…' : 'Jana Website'}
          </button>
        </form>
      </main>
    </div>
  )
}
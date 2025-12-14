/**
 * Website Creation Page with Live Preview
 */

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { ArrowLeft, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '../../../lib/api'
import { cn } from '../../../lib/utils'


/**
 * Types
 */
type WebsiteGenerationRequest = {
  business_name: string
  business_type: string
  description: string
  language: 'ms' | 'en'
  subdomain: string
  include_whatsapp: boolean
  whatsapp_number: string
  include_maps: boolean
  location_address: string
  include_ecommerce: boolean
  contact_email: string
}

/**
 * Helpers (LOCAL – safe)
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
    business_type: '',
    description: '',
    language: 'ms',
    subdomain: '',
    include_whatsapp: true,
    whatsapp_number: '',
    include_maps: true,
    location_address: '',
    include_ecommerce: false,
    contact_email: '',
  })

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target
    const newValue =
      type === 'checkbox'
        ? (e.target as HTMLInputElement).checked
        : value

    setFormData(prev => ({
      ...prev,
      [name]: newValue,
    }))

    if (name === 'business_name' && value) {
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

    if (formData.include_whatsapp && !formData.whatsapp_number) {
      toast.error('Sila masukkan nombor WhatsApp')
      return
    }

    setLoading(true)

    try {
      const response = await apiFetch('/api/generate-website', {
        method: 'POST',
        body: JSON.stringify(formData),
      })

      toast.success('Website sedang dijana!')
      router.push(`/dashboard`)
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

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold mb-6">Cipta Website Baharu</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
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

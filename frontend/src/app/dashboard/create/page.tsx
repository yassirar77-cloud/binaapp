/**
 * Website Creation Page with Live Preview
 */

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient, WebsiteGenerationRequest } from '@/lib/api'
import toast from 'react-hot-toast'
import { ArrowLeft, Sparkles, Eye } from 'lucide-react'
import Link from 'next/link'
import { slugify, validateSubdomain } from '@/lib/utils'

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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    const newValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value

    setFormData(prev => ({
      ...prev,
      [name]: newValue
    }))

    // Auto-generate subdomain from business name
    if (name === 'business_name' && value) {
      const slug = slugify(value)
      setFormData(prev => ({ ...prev, subdomain: slug }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!validateSubdomain(formData.subdomain)) {
      toast.error('Subdomain tidak sah. Gunakan huruf kecil, nombor, dan dash sahaja.')
      return
    }

    if (formData.include_whatsapp && !formData.whatsapp_number) {
      toast.error('Sila masukkan nombor WhatsApp')
      return
    }

    setLoading(true)

    try {
      const response = await apiClient.generateWebsite(formData)
      toast.success('Website sedang dijana! Ini akan mengambil masa beberapa minit.')
      router.push(`/dashboard/website/${response.data.id}`)
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Gagal menjana website'
      toast.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2 text-gray-600 hover:text-gray-900">
            <ArrowLeft className="w-5 h-5" />
            Kembali ke Dashboard
          </Link>
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Cipta Website Baharu</h1>
          <p className="text-gray-600">
            Beritahu kami tentang perniagaan anda dan AI kami akan jana website lengkap untuk anda
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Business Information */}
          <div className="card">
            <h2 className="text-xl font-bold mb-4">Maklumat Perniagaan</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Nama Perniagaan *
                </label>
                <input
                  type="text"
                  name="business_name"
                  value={formData.business_name}
                  onChange={handleChange}
                  className="input"
                  placeholder="Contoh: Kedai Runcit Ahmad"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Jenis Perniagaan
                </label>
                <input
                  type="text"
                  name="business_type"
                  value={formData.business_type}
                  onChange={handleChange}
                  className="input"
                  placeholder="Contoh: Kedai Runcit, Restoran, Servis"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Bahasa Website
                </label>
                <select
                  name="language"
                  value={formData.language}
                  onChange={handleChange}
                  className="input"
                >
                  <option value="ms">Bahasa Malaysia</option>
                  <option value="en">English</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Terangkan Perniagaan Anda *
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  className="input min-h-32"
                  placeholder="Contohnya: Kami menjual barang runcit harian seperti beras, minyak masak, susu, dan keperluan dapur. Kedai kami terletak di Kampung Baru dan beroperasi sejak 20 tahun. Kami juga menerima pesanan melalui WhatsApp untuk delivery."
                  required
                  minLength={10}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Terangkan dengan detail apa yang anda jual/tawarkan, di mana lokasi, dan apa yang istimewa tentang perniagaan anda.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Subdomain *
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    name="subdomain"
                    value={formData.subdomain}
                    onChange={handleChange}
                    className="input"
                    placeholder="kedairuncitahmad"
                    required
                    pattern="[a-z0-9]([a-z0-9-]*[a-z0-9])?"
                  />
                  <span className="text-gray-600 whitespace-nowrap">.binaapp.my</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Website anda akan berada di: https://{formData.subdomain || 'namaanda'}.binaapp.my
                </p>
              </div>
            </div>
          </div>

          {/* Integrations */}
          <div className="card">
            <h2 className="text-xl font-bold mb-4">Integrasi</h2>

            <div className="space-y-6">
              {/* WhatsApp */}
              <div className="border rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    name="include_whatsapp"
                    checked={formData.include_whatsapp}
                    onChange={handleChange}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <h3 className="font-semibold">WhatsApp Ordering 📱</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Butang WhatsApp floating untuk pelanggan hubungi dan order
                    </p>
                    {formData.include_whatsapp && (
                      <input
                        type="tel"
                        name="whatsapp_number"
                        value={formData.whatsapp_number}
                        onChange={handleChange}
                        className="input"
                        placeholder="+60123456789"
                      />
                    )}
                  </div>
                </div>
              </div>

              {/* Google Maps */}
              <div className="border rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    name="include_maps"
                    checked={formData.include_maps}
                    onChange={handleChange}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <h3 className="font-semibold">Google Maps 🗺️</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      Tunjukkan lokasi perniagaan anda
                    </p>
                    {formData.include_maps && (
                      <input
                        type="text"
                        name="location_address"
                        value={formData.location_address}
                        onChange={handleChange}
                        className="input"
                        placeholder="No 123, Jalan Merdeka, Kuala Lumpur"
                      />
                    )}
                  </div>
                </div>
              </div>

              {/* E-commerce */}
              <div className="border rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    name="include_ecommerce"
                    checked={formData.include_ecommerce}
                    onChange={handleChange}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <h3 className="font-semibold">Shopping Cart 🛒</h3>
                    <p className="text-sm text-gray-600">
                      Sistem cart dan checkout untuk jualan online
                    </p>
                  </div>
                </div>
              </div>

              {/* Contact Email */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Email untuk Contact Form
                </label>
                <input
                  type="email"
                  name="contact_email"
                  value={formData.contact_email}
                  onChange={handleChange}
                  className="input"
                  placeholder="email@perniagaan.com"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Pesanan dari contact form akan dihantar ke email ini
                </p>
              </div>
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-900">
                <strong>Bonus:</strong> Setiap website automatik termasuk Contact Form, QR Code, dan Social Sharing buttons!
              </p>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  Menjana Website...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Jana Website dengan AI
                </>
              )}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}

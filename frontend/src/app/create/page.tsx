'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  Sparkles, Download, Upload, Eye, Copy, Check, Share2, Layout
} from 'lucide-react'

import ImageUpload from './components/ImageUpload'
import DevicePreview from './components/DevicePreview'
import MultiDevicePreview from './components/MultiDevicePreview'

const API_BASE = process.env.NEXT_PUBLIC_API_URL!

const EXAMPLES = [
  {
    title: 'Kedai Nasi Kandar',
    lang: 'ms',
    text: 'Saya ada kedai nasi kandar di Penang. Kami jual nasi kandar, ayam goreng, ikan bakar, dan pelbagai lauk. Menu dari RM5-RM15. Terletak di Jalan Burma. Telefon 019-5551234.'
  },
  {
    title: 'Hair Salon',
    lang: 'en',
    text: 'Modern hair salon in KL offering haircut and coloring. Prices RM50-RM300. WhatsApp 012-3456789.'
  }
]

interface StyleVariation {
  style: string
  html: string
}

export default function CreatePage() {
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [html, setHtml] = useState('')
  const [variations, setVariations] = useState<StyleVariation[]>([])
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null)
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  const [multiStyle, setMultiStyle] = useState(true)
  const [previewMode, setPreviewMode] = useState<'single' | 'multi'>('single')

  const handleGenerate = async () => {
    if (description.length < 10) {
      setError('Description too short')
      return
    }

    setLoading(true)
    setError('')
    setHtml('')
    setVariations([])
    setSelectedStyle(null)

    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          user_id: 'demo-user',
          images: uploadedImages,
          multi_style: multiStyle
        })
      })

      if (!res.ok) throw new Error('Generate failed')

      const data = await res.json()

      if (data.variations) {
        const list = Object.entries(data.variations).map(
          ([style, v]: any) => ({
            style,
            html: v.html || v.html_content || ''
          })
        )
        setVariations(list)
      } else {
        setHtml(data.html || data.html_content)
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="font-bold text-xl">BinaApp</span>
          </Link>
          <Link href="/" className="btn btn-outline btn-sm">Home</Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold mb-4">Create Website with AI</h1>

        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full h-48 p-4 border rounded-lg"
          placeholder="Describe your business..."
        />

        <div className="mt-4">
          <ImageUpload onImagesUploaded={setUploadedImages} />
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="btn btn-primary w-full mt-6"
        >
          {loading ? 'Generating...' : 'Generate Website'}
        </button>

        {variations.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
            {variations.map(v => (
              <div
                key={v.style}
                onClick={() => {
                  setSelectedStyle(v.style)
                  setHtml(v.html)
                }}
                className="border rounded-lg cursor-pointer hover:border-primary-500"
              >
                <div className="p-2 text-center font-semibold capitalize">
                  {v.style}
                </div>
                <iframe
                  srcDoc={v.html}
                  className="w-full h-64 border-0"
                  sandbox="allow-same-origin"
                />
              </div>
            ))}
          </div>
        )}

        {html && (
          <div className="mt-10">
            {previewMode === 'single' ? (
              <DevicePreview htmlContent={html} title="Preview" />
            ) : (
              <MultiDevicePreview htmlContent={html} title="Multi Device" />
            )}
          </div>
        )}
      </main>
    </div>
  )
}

/**
 * Create Page - AI Website Generation
 */
'use client'
import { useState } from 'react'
import Link from 'next/link'
import { Sparkles, Download, Upload, Eye, Copy, Check, Share2, Layout } from 'lucide-react'
import ImageUpload from './components/ImageUpload'
import DevicePreview from './components/DevicePreview'
import MultiDevicePreview from './components/MultiDevicePreview'
import { API_BASE_URL } from '@/lib/env'   // ✅ FIX 1

const EXAMPLE_DESCRIPTIONS = [
  {
    title: 'Kedai Nasi Kandar',
    lang: 'ms',
    text: 'Saya ada kedai nasi kandar di Penang. Kami jual nasi kandar, ayam goreng, ikan bakar, dan pelbagai lauk. Menu dari RM5-RM15. Kami terletak di Jalan Burma, Penang. Telefon 019-5551234. Buka 7am-11pm setiap hari.'
  },
  {
    title: 'Hair Salon Booking',
    lang: 'en',
    text: 'Modern hair salon in KL offering haircuts, coloring, and styling. Prices from RM50-RM300. Located at Bukit Bintang. Book appointments via WhatsApp 012-3456789. Open Tuesday-Sunday 10am-8pm.'
  },
  {
    title: 'Photography Portfolio',
    lang: 'en',
    text: 'Professional photographer specializing in weddings and events. Based in Selangor. Contact via WhatsApp 011-23456789 or email hello@photos.com. View my portfolio and book your session today.'
  },
  {
    title: 'Butik Pakaian Online',
    lang: 'ms',
    text: 'Butik online menjual pakaian wanita, baju kurung, tudung, dan aksesori. Harga dari RM30-RM200. Hantar ke seluruh Malaysia. WhatsApp untuk order: 013-8889999. Instagram: @butikkita'
  }
]

interface StyleVariation {
  style: string
  html: string
  preview_image?: string
  thumbnail?: string
  social_preview?: string
}

export default function CreatePage() {
  const [description, setDescription] = useState('')
  const [language, setLanguage] = useState<'ms' | 'en'>('ms')
  const [loading, setLoading] = useState(false)
  const [generatedHtml, setGeneratedHtml] = useState('')
  const [detectedFeatures, setDetectedFeatures] = useState<string[]>([])
  const [templateUsed, setTemplateUsed] = useState('')
  const [error, setError] = useState('')
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [subdomain, setSubdomain] = useState('')
  const [projectName, setProjectName] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [publishedUrl, setPublishedUrl] = useState('')
  const [copied, setCopied] = useState(false)
  const [uploadedImages, setUploadedImages] = useState<string[]>([])
  
  const [multiStyle, setMultiStyle] = useState(true)
  const [styleVariations, setStyleVariations] = useState<StyleVariation[]>([])
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null)
  const [generatePreviews, setGeneratePreviews] = useState(false)
  const [previewMode, setPreviewMode] = useState<'single' | 'multi'>('single')

  const handleGenerate = async () => {
    if (description.length < 10) {
      setError('Please provide a more detailed description (at least 10 characters)')
      return
    }

    setLoading(true)
    setError('')
    setGeneratedHtml('')
    setStyleVariations([])
    setSelectedStyle(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/simple/generate`, {   // ✅ FIX 2
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          user_id: 'demo-user',
          images: uploadedImages,
          multi_style: multiStyle,
          generate_previews: generatePreviews
        })
      })

      if (!response.ok) throw new Error(`Failed to generate: ${response.statusText}`)
      const data = await response.json()

      if (multiStyle && data.variations) {
        const formatted = Object.entries(data.variations).map(([style, content]: any) => ({
          style,
          html: content.html_content || content.html || '',
          thumbnail: content.thumbnail || null,
          preview_image: content.preview_image || null,
          social_preview: content.social_preview || null
        }))
        setStyleVariations(formatted)
        setDetectedFeatures(data.detected_features || [])
        setTemplateUsed(data.template_used || 'general')
      } else {
        setGeneratedHtml(data.html || data.html_content)
        setDetectedFeatures(data.detected_features || [])
        setTemplateUsed(data.template_used || 'general')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate website.')
    } finally {
      setLoading(false)
    }
  }

  const handlePublish = async () => {
    if (!subdomain || !projectName) {
      setError('Please fill in subdomain and project name')
      return
    }

    setPublishing(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/simple/publish`, {   // ✅ FIX 3
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          html_content: generatedHtml,
          subdomain,
          project_name: projectName,
          user_id: 'demo-user'
        })
      })

      if (!response.ok) throw new Error('Publish failed')
      const data = await response.json()
      setPublishedUrl(data.url)
      setShowPublishModal(false)
    } catch (err: any) {
      setError(err.message || 'Publish failed')
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* UI CODE CONTINUES UNCHANGED */}
    </div>
  )
}

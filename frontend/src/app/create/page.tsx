/**
 * Create Page - AI Website Generation
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Sparkles, Download, Upload, Eye, Copy, Check } from 'lucide-react'
import ImageUpload from './components/ImageUpload'

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

  // Multi-style generation state
  const [multiStyle, setMultiStyle] = useState(true)
  const [styleVariations, setStyleVariations] = useState<StyleVariation[]>([])
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null)

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
      const response = await fetch('http://localhost:8000/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          description,
          user_id: 'demo-user',
          images: uploadedImages,
          multi_style: multiStyle
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to generate: ${response.statusText}`)
      }

      const data = await response.json()

      // Handle multi-style response
      if (multiStyle && data.variations) {
        setStyleVariations(data.variations)
        setDetectedFeatures(data.detected_features || [])
        setTemplateUsed(data.template_used || 'general')
      } else {
        // Single style response (backward compatibility)
        setGeneratedHtml(data.html)
        setDetectedFeatures(data.detected_features || [])
        setTemplateUsed(data.template_used || 'general')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate website. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectVariation = (variation: StyleVariation) => {
    setSelectedStyle(variation.style)
    setGeneratedHtml(variation.html)
  }

  const handleBackToVariations = () => {
    setSelectedStyle(null)
    setGeneratedHtml('')
  }

  const handleDownload = () => {
    const blob = new Blob([generatedHtml], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'website.html'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopyHtml = () => {
    navigator.clipboard.writeText(generatedHtml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handlePublish = async () => {
    if (!subdomain || !projectName) {
      setError('Please fill in subdomain and project name')
      return
    }

    setPublishing(true)
    setError('')

    try {
      const response = await fetch('http://localhost:8000/api/publish', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          html_content: generatedHtml,
          subdomain: subdomain.toLowerCase().replace(/[^a-z0-9-]/g, ''),
          project_name: projectName,
          user_id: 'demo-user'
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to publish')
      }

      const data = await response.json()
      setPublishedUrl(data.url)
      setShowPublishModal(false)
    } catch (err: any) {
      setError(err.message || 'Failed to publish website. Please try again.')
    } finally {
      setPublishing(false)
    }
  }

  const fillExample = (example: typeof EXAMPLE_DESCRIPTIONS[0]) => {
    setDescription(example.text)
    setLanguage(example.lang as 'ms' | 'en')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-sm text-gray-600 hover:text-gray-900">
              My Projects
            </Link>
            <Link href="/" className="btn btn-outline btn-sm">
              Back to Home
            </Link>
          </div>
        </nav>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-3">
            ✨ Create Your Website with AI
          </h1>
          <p className="text-gray-600 text-lg">
            Describe your business in Bahasa Malaysia or English, and let AI build your website
          </p>
        </div>

        {/* Main Content */}
        {!generatedHtml ? (
          <div className="max-w-4xl mx-auto">
            {/* Menu Designer Link */}
            <div style={{ marginBottom: '20px' }}>
              <a href="/menu-designer" style={{
                display: 'inline-block',
                padding: '12px 24px',
                background: '#16a34a',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '8px',
                fontWeight: 'bold'
              }}>
                🍽️ Create Print Menu
              </a>
            </div>

            {/* Example Buttons */}
            <div className="mb-6">
              <label className="block text-sm font-semibold mb-3 text-gray-700">
                Try an example:
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {EXAMPLE_DESCRIPTIONS.map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => fillExample(example)}
                    className="btn btn-outline btn-sm text-left justify-start"
                  >
                    {example.title}
                  </button>
                ))}
              </div>
            </div>

            {/* Language Toggle */}
            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2 text-gray-700">
                Language:
              </label>
              <div className="flex gap-3">
                <button
                  onClick={() => setLanguage('ms')}
                  className={`btn ${language === 'ms' ? 'btn-primary' : 'btn-outline'}`}
                >
                  🇲🇾 Bahasa Malaysia
                </button>
                <button
                  onClick={() => setLanguage('en')}
                  className={`btn ${language === 'en' ? 'btn-primary' : 'btn-outline'}`}
                >
                  🇬🇧 English
                </button>
              </div>
            </div>

            {/* Multi-Style Toggle */}
            <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={multiStyle}
                  onChange={(e) => setMultiStyle(e.target.checked)}
                  className="w-5 h-5 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <div>
                  <span className="font-semibold text-gray-900">
                    ✨ Generate Multiple Styles (Recommended)
                  </span>
                  <p className="text-sm text-gray-600 mt-1">
                    Get 3 design variations (Modern, Minimal, Bold) and choose your favorite
                  </p>
                </div>
              </label>
            </div>

            {/* Description Textarea */}
            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2 text-gray-700">
                Describe your business:
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={
                  language === 'ms'
                    ? 'Contoh: Saya ada kedai runcit di Shah Alam yang jual barangan harian, makanan, dan minuman. Harga berpatutan dari RM1. Lokasi di Seksyen 7 Shah Alam. Telefon 019-1234567. Buka 7am-10pm setiap hari...'
                    : 'Example: I have a coffee shop in Kuala Lumpur serving specialty coffee, cakes, and light meals. Prices from RM8. Located at TTDI. Contact via WhatsApp 012-3456789. Open daily 8am-6pm...'
                }
                className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              />
              <div className="text-right text-sm text-gray-500 mt-1">
                {description.length} characters
              </div>
            </div>

            {/* Image Upload */}
            <ImageUpload onImagesUploaded={setUploadedImages} />

            {/* Error Message */}
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={loading || description.length < 10}
              className="w-full btn btn-primary text-lg py-4 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Generating your website...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 mr-2" />
                  Generate Website with AI
                </>
              )}
            </button>
          </div>
        ) : styleVariations.length > 0 && !selectedStyle ? (
          /* Multi-Style Variations View */
          <div className="max-w-7xl mx-auto">
            {/* Success Message */}
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 text-green-800 font-semibold mb-2">
                <Check className="w-5 h-5" />
                3 Design Variations Generated!
              </div>
              <p className="text-sm text-green-700">
                Template: <span className="font-semibold">{templateUsed}</span> •
                Features: <span className="font-semibold">{detectedFeatures.join(', ')}</span>
              </p>
              <p className="text-sm text-green-700 mt-2">
                Click on any design below to view and customize it
              </p>
            </div>

            {/* Back Button */}
            <button
              onClick={() => {
                setStyleVariations([])
                setError('')
                setPublishedUrl('')
              }}
              className="mb-6 btn btn-outline"
            >
              Create Another
            </button>

            {/* Variations Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              {styleVariations.map((variation, idx) => {
                const styleInfo = {
                  modern: {
                    name: 'Modern',
                    icon: '🎨',
                    color: 'from-purple-500 to-blue-500',
                    description: 'Vibrant gradients, glassmorphism, contemporary design'
                  },
                  minimal: {
                    name: 'Minimal',
                    icon: '✨',
                    color: 'from-gray-700 to-gray-900',
                    description: 'Clean, simple, elegant with lots of white space'
                  },
                  bold: {
                    name: 'Bold',
                    icon: '⚡',
                    color: 'from-orange-500 to-red-500',
                    description: 'High contrast, dramatic, attention-grabbing'
                  }
                }[variation.style] || {
                  name: variation.style,
                  icon: '🎯',
                  color: 'from-blue-500 to-indigo-500',
                  description: 'Custom style'
                }

                return (
                  <div
                    key={idx}
                    className="group bg-white rounded-xl shadow-lg overflow-hidden border-2 border-transparent hover:border-primary-500 transition-all duration-300 cursor-pointer transform hover:scale-105"
                    onClick={() => handleSelectVariation(variation)}
                  >
                    {/* Header */}
                    <div className={`bg-gradient-to-r ${styleInfo.color} p-4 text-white`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-2xl">{styleInfo.icon}</span>
                        <h3 className="text-xl font-bold">{styleInfo.name}</h3>
                      </div>
                      <p className="text-sm opacity-90">{styleInfo.description}</p>
                    </div>

                    {/* Preview */}
                    <div className="relative bg-gray-100" style={{ height: '400px' }}>
                      <iframe
                        srcDoc={variation.html}
                        className="w-full h-full border-0 pointer-events-none"
                        title={`${styleInfo.name} Preview`}
                        sandbox="allow-same-origin"
                      />
                      {/* Overlay on hover */}
                      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center">
                        <button className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-white text-primary-600 px-6 py-3 rounded-lg font-semibold shadow-lg">
                          <Eye className="w-5 h-5 inline-block mr-2" />
                          View Full Design
                        </button>
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="p-4 bg-gray-50 text-center">
                      <p className="text-sm text-gray-600">Click to view and customize</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ) : (
          <div className="max-w-7xl mx-auto">
            {/* Success Message */}
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 text-green-800 font-semibold mb-2">
                <Check className="w-5 h-5" />
                Website Generated Successfully!
              </div>
              <p className="text-sm text-green-700">
                Template: <span className="font-semibold">{templateUsed}</span> •
                Features: <span className="font-semibold">{detectedFeatures.join(', ')}</span>
                {selectedStyle && (
                  <>
                    {' • '}
                    Style: <span className="font-semibold capitalize">{selectedStyle}</span>
                  </>
                )}
              </p>
            </div>

            {publishedUrl && (
              <div className="mb-6 p-6 bg-blue-50 border-2 border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 text-blue-800 font-bold mb-3 text-lg">
                  🎉 Website Published!
                </div>
                <p className="text-blue-700 mb-3">
                  Your website is now live at:
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={publishedUrl}
                    readOnly
                    className="flex-1 px-4 py-2 bg-white border border-blue-300 rounded-lg"
                  />
                  <a
                    href={publishedUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    View Live
                  </a>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3 mb-6">
              {selectedStyle && styleVariations.length > 0 && (
                <button
                  onClick={handleBackToVariations}
                  className="btn btn-outline"
                >
                  ← Back to Variations
                </button>
              )}
              <button
                onClick={handleDownload}
                className="btn btn-outline"
              >
                <Download className="w-4 h-4 mr-2" />
                Download HTML
              </button>
              <button
                onClick={handleCopyHtml}
                className="btn btn-outline"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 mr-2" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 mr-2" />
                    Copy HTML
                  </>
                )}
              </button>
              <button
                onClick={() => setShowPublishModal(true)}
                className="btn btn-primary"
              >
                <Upload className="w-4 h-4 mr-2" />
                Publish Website
              </button>
              <button
                onClick={() => {
                  setGeneratedHtml('')
                  setStyleVariations([])
                  setSelectedStyle(null)
                  setError('')
                  setPublishedUrl('')
                }}
                className="btn btn-outline"
              >
                Create Another
              </button>
            </div>

            {/* Preview */}
            <div className="bg-white rounded-lg shadow-lg overflow-hidden">
              <div className="bg-gray-800 text-white px-4 py-3 flex items-center justify-between">
                <span className="font-semibold">Preview</span>
                <span className="text-sm text-gray-400">Scroll to see full website</span>
              </div>
              <div className="relative" style={{ height: '70vh' }}>
                <iframe
                  srcDoc={generatedHtml}
                  className="w-full h-full border-0"
                  title="Website Preview"
                  sandbox="allow-same-origin allow-scripts allow-forms"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Publish Modal */}
      {showPublishModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h2 className="text-2xl font-bold mb-4">Publish Your Website</h2>

            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="My Restaurant"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-semibold mb-2">
                Choose Subdomain
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                  placeholder="kedaiayam"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                />
                <span className="text-gray-600">.binaapp.my</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Only lowercase letters, numbers, and hyphens
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowPublishModal(false)
                  setError('')
                }}
                className="flex-1 btn btn-outline"
                disabled={publishing}
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                className="flex-1 btn btn-primary"
                disabled={publishing || !subdomain || !projectName}
              >
                {publishing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Publishing...
                  </>
                ) : (
                  'Publish Now'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

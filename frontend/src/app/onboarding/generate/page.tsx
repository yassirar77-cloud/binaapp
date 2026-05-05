'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Loader2, Sparkles, AlertCircle, RotateCcw } from 'lucide-react'
import ProgressBar from '../ProgressBar'
import { useOnboardingState } from '@/hooks/useOnboardingState'
import { DIRECT_BACKEND_URL } from '@/lib/env'
import { getCurrentUser, getStoredToken } from '@/lib/supabase'

export default function GeneratePage() {
  const router = useRouter()
  const { state, reset } = useOnboardingState()
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState('')

  async function handleGenerate() {
    setGenerating(true)
    setError('')
    setProgress('Sedang mencipta laman web anda... ini ambil masa 30 saat')

    try {
      const user = await getCurrentUser()
      const token = getStoredToken()

      // Build image_map from uploaded photos
      const imageMap: Record<string, string> = {}
      for (const photo of state.photos) {
        if (photo.url) {
          imageMap[photo.slot] = photo.url
        }
      }

      // Build menu description from dishes
      const dishDescriptions = state.dishes
        .filter(d => d.name)
        .map(d => `${d.name} - ${d.description} (RM${d.price})`)
        .join('. ')

      // Build images array for backend
      const allImages = state.photos
        .filter(p => p.url)
        .map(p => ({
          url: p.url,
          name: p.slot === 'hero' ? 'Hero' : p.slot === 'interior' ? 'Interior' : `Menu ${p.slot.split('_')[1]}`,
          price: '',
        }))

      // Gallery metadata
      const galleryMetadata = state.dishes
        .filter(d => d.name && d.photoUrl)
        .map(d => ({ url: d.photoUrl, name: d.name, price: `RM${d.price}` }))

      const description = dishDescriptions
        ? `Restoran Malaysia. Menu: ${dishDescriptions}`
        : 'Restoran Malaysia dengan pelbagai hidangan tempatan.'

      setProgress('Menghantar ke AI...')

      const startResponse = await fetch(`${DIRECT_BACKEND_URL}/api/generate/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          description,
          business_description: description,
          language: 'ms',
          user_id: user?.id || 'anonymous',
          email: user?.email,
          images: allImages.length > 0 ? allImages : undefined,
          gallery_metadata: galleryMetadata.length > 0 ? galleryMetadata : undefined,
          image_choice: allImages.length > 0 ? 'uploaded' : 'ai',
          color_mode: 'light',
          style_dna: state.styleDna,
          features: {
            whatsapp: true,
            googleMap: false,
            deliverySystem: false,
            contactForm: false,
            socialMedia: false,
          },
        }),
      })

      if (!startResponse.ok) {
        const errData = await startResponse.json().catch(() => ({}))
        throw new Error(errData.detail || errData.message || `Server error ${startResponse.status}`)
      }

      const startData = await startResponse.json()
      const jobId = startData.job_id

      if (!jobId) {
        throw new Error('Tiada job_id dari server')
      }

      setProgress('AI sedang menjana laman web anda...')

      // Poll for completion
      let attempts = 0
      const maxAttempts = 60 // 2 minutes

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000))
        attempts++

        const statusRes = await fetch(`${DIRECT_BACKEND_URL}/api/generate/status/${jobId}?t=${Date.now()}`)
        const statusData = await statusRes.json()

        if (statusData.status === 'complete' || statusData.status === 'completed') {
          // Success! Navigate to the generated site
          setProgress('Siap! Mengalihkan...')
          reset()

          if (statusData.website_id) {
            router.push(`/edit/${statusData.website_id}`)
          } else if (statusData.redirect_url) {
            router.push(statusData.redirect_url)
          } else {
            router.push('/dashboard')
          }
          return
        }

        if (statusData.status === 'failed' || statusData.status === 'error') {
          throw new Error(statusData.error || 'Penjanaan gagal')
        }

        // Update progress message
        if (statusData.progress) {
          const pct = Math.round(statusData.progress * 100)
          setProgress(`AI sedang menjana... ${pct}%`)
        }
      }

      throw new Error('Timeout — penjanaan mengambil masa terlalu lama')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Ralat tidak dijangka'
      setError(msg)
      setProgress('')
    } finally {
      setGenerating(false)
    }
  }

  // Summary of what will be generated
  const photoCount = state.photos.length
  const dishCount = state.dishes.filter(d => d.name).length
  const styleName = state.styleDna?.replace(/_/g, ' ') || 'Default'

  return (
    <>
      <ProgressBar currentStep={4} />

      <div className="text-center mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
          Cipta Laman Web Anda
        </h1>
        <p className="text-gray-600">
          Semak ringkasan dan tekan butang untuk mencipta.
        </p>
      </div>

      {/* Summary card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-8">
        <h3 className="font-semibold text-gray-900 mb-4">Ringkasan</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Foto dimuat naik</span>
            <span className="font-medium">{photoCount} foto</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Hidangan</span>
            <span className="font-medium">{dishCount} item</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Gaya</span>
            <span className="font-medium capitalize">{styleName}</span>
          </div>
        </div>

        {/* Dish preview */}
        {dishCount > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-xs text-gray-500 mb-2">Hidangan:</p>
            <div className="flex flex-wrap gap-2">
              {state.dishes.filter(d => d.name).map((d, i) => (
                <span
                  key={i}
                  className="px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-full"
                >
                  {d.name} — RM{d.price}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
          <AlertCircle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-800 font-medium text-sm">Penjanaan gagal</p>
            <p className="text-red-600 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Generate button */}
      <div className="text-center mb-8">
        {generating ? (
          <div className="inline-flex flex-col items-center gap-3">
            <Loader2 size={40} className="animate-spin text-orange-500" />
            <p className="text-gray-600 text-sm">{progress}</p>
          </div>
        ) : (
          <button
            onClick={handleGenerate}
            className="px-8 py-4 bg-orange-500 text-white font-bold text-lg rounded-xl hover:bg-orange-600 transition-colors shadow-lg hover:shadow-xl flex items-center gap-3 mx-auto"
          >
            <Sparkles size={22} />
            Cipta Laman Web Saya
          </button>
        )}

        {error && !generating && (
          <button
            onClick={handleGenerate}
            className="mt-4 px-5 py-2 border border-orange-300 text-orange-600 rounded-lg hover:bg-orange-50 transition-colors flex items-center gap-2 mx-auto"
          >
            <RotateCcw size={16} />
            Cuba lagi
          </button>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => router.push('/onboarding/style')}
          disabled={generating}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50"
        >
          <ArrowLeft size={18} />
          Kembali
        </button>
      </div>
    </>
  )
}

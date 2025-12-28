'use client'

import { useState } from 'react'
import { API_BASE_URL } from '@/lib/env'

interface VisualImageUploadProps {
  onImagesUploaded: (images: { hero: string | null; gallery: string[] }) => void
}

export default function VisualImageUpload({ onImagesUploaded }: VisualImageUploadProps) {
  const [heroImage, setHeroImage] = useState<File | null>(null)
  const [heroPreview, setHeroPreview] = useState<string>('')
  const [heroUrl, setHeroUrl] = useState<string>('')

  const [galleryImages, setGalleryImages] = useState<(File | null)[]>([null, null, null, null])
  const [galleryPreviews, setGalleryPreviews] = useState<string[]>(['', '', '', ''])
  const [galleryUrls, setGalleryUrls] = useState<string[]>(['', '', '', ''])

  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState('')

  const uploadImage = async (file: File): Promise<string> => {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(`${API_BASE_URL}/api/upload-image`, {
      method: 'POST',
      body: formData
    })

    const data = await res.json()

    if (data.success) {
      return data.url
    }
    throw new Error('Upload failed')
  }

  const handleHeroUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setHeroImage(file)
      const preview = URL.createObjectURL(file)
      setHeroPreview(preview)

      // Upload immediately
      setUploading(true)
      setUploadProgress('Uploading hero image...')
      try {
        const url = await uploadImage(file)
        setHeroUrl(url)
        // Notify parent
        onImagesUploaded({
          hero: url,
          gallery: galleryUrls.filter(u => u !== '')
        })
      } catch (error) {
        console.error('Hero upload failed:', error)
      } finally {
        setUploading(false)
        setUploadProgress('')
      }
    }
  }

  const handleGalleryUpload = async (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const newImages = [...galleryImages]
      newImages[index] = file
      setGalleryImages(newImages)

      const preview = URL.createObjectURL(file)
      const newPreviews = [...galleryPreviews]
      newPreviews[index] = preview
      setGalleryPreviews(newPreviews)

      // Upload immediately
      setUploading(true)
      setUploadProgress(`Uploading gallery image ${index + 1}...`)
      try {
        const url = await uploadImage(file)
        const newUrls = [...galleryUrls]
        newUrls[index] = url
        setGalleryUrls(newUrls)

        // Notify parent
        onImagesUploaded({
          hero: heroUrl || null,
          gallery: newUrls.filter(u => u !== '')
        })
      } catch (error) {
        console.error(`Gallery ${index + 1} upload failed:`, error)
      } finally {
        setUploading(false)
        setUploadProgress('')
      }
    }
  }

  const removeHero = () => {
    setHeroImage(null)
    setHeroPreview('')
    setHeroUrl('')
    onImagesUploaded({
      hero: null,
      gallery: galleryUrls.filter(u => u !== '')
    })
  }

  const removeGallery = (index: number) => {
    const newImages = [...galleryImages]
    newImages[index] = null
    setGalleryImages(newImages)

    const newPreviews = [...galleryPreviews]
    newPreviews[index] = ''
    setGalleryPreviews(newPreviews)

    const newUrls = [...galleryUrls]
    newUrls[index] = ''
    setGalleryUrls(newUrls)

    onImagesUploaded({
      hero: heroUrl || null,
      gallery: newUrls.filter(u => u !== '')
    })
  }

  const uploadedCount = (heroImage ? 1 : 0) + galleryImages.filter(img => img !== null).length

  return (
    <div className="bg-white rounded-xl p-6 shadow-lg mb-6">
      <h3 className="text-lg font-bold mb-2">📸 Muat Naik Gambar Anda / Upload Your Images</h3>
      <p className="text-gray-500 text-sm mb-4">
        Pilih gambar untuk setiap bahagian. Jika tidak muat naik, AI akan jana gambar automatik.
        <br />
        <span className="text-xs">Choose images for each section. If not uploaded, AI will generate images automatically.</span>
      </p>

      {uploading && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <p className="text-blue-700 text-sm font-medium">{uploadProgress}</p>
          </div>
        </div>
      )}

      {/* HERO IMAGE - Large Banner */}
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">
          🖼️ Gambar Utama (Hero Banner)
        </label>
        <p className="text-xs text-gray-400 mb-2">Gambar besar di bahagian atas website / Large image at the top of the website</p>
        <div
          className="border-2 border-dashed border-gray-300 rounded-xl p-4 text-center cursor-pointer hover:border-blue-500 transition"
          onClick={() => document.getElementById('hero-upload')?.click()}
        >
          {heroPreview ? (
            <div className="relative">
              <img src={heroPreview} alt="Hero" className="w-full h-40 object-cover rounded-lg" />
              <button
                onClick={(e) => { e.stopPropagation(); removeHero(); }}
                className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 text-xs hover:bg-red-600"
                title="Remove image"
              >✕</button>
              {heroUrl && (
                <div className="absolute bottom-2 left-2 bg-green-500 text-white text-xs px-2 py-1 rounded">
                  ✓ Uploaded
                </div>
              )}
            </div>
          ) : (
            <div className="py-8">
              <span className="text-4xl">🖼️</span>
              <p className="text-gray-500 mt-2">Klik untuk muat naik gambar hero / Click to upload hero image</p>
              <p className="text-xs text-gray-400">Saiz dicadangkan / Recommended size: 1920 x 600 piksel</p>
            </div>
          )}
        </div>
        <input
          id="hero-upload"
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleHeroUpload}
          disabled={uploading}
        />
      </div>

      {/* GALLERY/PRODUCT IMAGES - 4 boxes */}
      <div>
        <label className="block text-sm font-medium mb-2">
          📷 Gambar Produk / Galeri (4 gambar)
        </label>
        <p className="text-xs text-gray-400 mb-3">
          Gambar menu, produk, atau perkhidmatan anda / Images of your menu, products, or services
        </p>

        <div className="grid grid-cols-2 gap-3">
          {[0, 1, 2, 3].map((index) => (
            <div
              key={index}
              className="border-2 border-dashed border-gray-300 rounded-xl p-2 text-center cursor-pointer hover:border-blue-500 transition aspect-square flex items-center justify-center"
              onClick={() => document.getElementById(`gallery-upload-${index}`)?.click()}
            >
              {galleryPreviews[index] ? (
                <div className="relative w-full h-full">
                  <img
                    src={galleryPreviews[index]}
                    alt={`Product ${index + 1}`}
                    className="w-full h-full object-cover rounded-lg"
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      removeGallery(index)
                    }}
                    className="absolute top-1 right-1 bg-red-500 text-white rounded-full w-5 h-5 text-xs hover:bg-red-600"
                    title="Remove image"
                  >✕</button>
                  <span className="absolute bottom-1 left-1 bg-black/50 text-white text-xs px-2 py-1 rounded">
                    Gambar {index + 1}
                  </span>
                  {galleryUrls[index] && (
                    <div className="absolute top-1 left-1 bg-green-500 text-white text-xs px-2 py-1 rounded">
                      ✓
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <span className="text-2xl">📷</span>
                  <p className="text-xs text-gray-500 mt-1">Gambar {index + 1}</p>
                </div>
              )}
              <input
                id={`gallery-upload-${index}`}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => handleGalleryUpload(index, e)}
                disabled={uploading}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Upload status */}
      <div className="mt-4 text-sm text-gray-500">
        ✅ {uploadedCount} / 5 gambar dipilih ({galleryUrls.filter(u => u !== '').length + (heroUrl ? 1 : 0)} uploaded)
      </div>
    </div>
  )
}

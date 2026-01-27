'use client'

import { useState } from 'react'
import { API_BASE_URL } from '@/lib/env'

interface GalleryImage {
  url: string
  name: string
  price: string
}

interface VisualImageUploadProps {
  onImagesUploaded: (images: { hero: string | null; gallery: GalleryImage[] }) => void
}

export default function VisualImageUpload({ onImagesUploaded }: VisualImageUploadProps) {
  const [heroImage, setHeroImage] = useState<File | null>(null)
  const [heroPreview, setHeroPreview] = useState<string>('')
  const [heroUrl, setHeroUrl] = useState<string>('')

  // Dynamic menu items - start with 1 empty item
  const [menuItems, setMenuItems] = useState<{
    file: File | null
    preview: string
    url: string
    name: string
    price: string
  }[]>([
    { file: null, preview: '', url: '', name: '', price: '' }
  ])

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

  // Notify parent of current state
  const notifyParent = (items: typeof menuItems, hero: string | null) => {
    onImagesUploaded({
      hero: hero,
      gallery: items
        .filter(g => g.url !== '' || g.name !== '' || g.price !== '')
        .map(g => ({ url: g.url, name: g.name, price: g.price }))
    })
  }

  const handleHeroUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setHeroImage(file)
      const preview = URL.createObjectURL(file)
      setHeroPreview(preview)

      // Upload immediately
      setUploading(true)
      setUploadProgress('Memuat naik gambar hero...')
      try {
        const url = await uploadImage(file)
        setHeroUrl(url)
        notifyParent(menuItems, url)
      } catch (error) {
        console.error('Hero upload failed:', error)
      } finally {
        setUploading(false)
        setUploadProgress('')
      }
    }
  }

  const handleMenuImageUpload = async (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const preview = URL.createObjectURL(file)
      const newItems = [...menuItems]
      newItems[index] = { ...newItems[index], file, preview }
      setMenuItems(newItems)

      // Upload immediately
      setUploading(true)
      setUploadProgress(`Memuat naik gambar item ${index + 1}...`)
      try {
        const url = await uploadImage(file)
        const updatedItems = [...newItems]
        updatedItems[index] = { ...updatedItems[index], url }
        setMenuItems(updatedItems)
        notifyParent(updatedItems, heroUrl || null)
      } catch (error) {
        console.error(`Menu item ${index + 1} upload failed:`, error)
      } finally {
        setUploading(false)
        setUploadProgress('')
      }
    }
  }

  const handleNameChange = (index: number, name: string) => {
    const newItems = [...menuItems]
    newItems[index] = { ...newItems[index], name }
    setMenuItems(newItems)
    notifyParent(newItems, heroUrl || null)
  }

  const handlePriceChange = (index: number, price: string) => {
    const newItems = [...menuItems]
    newItems[index] = { ...newItems[index], price }
    setMenuItems(newItems)
    notifyParent(newItems, heroUrl || null)
  }

  const removeHero = () => {
    setHeroImage(null)
    setHeroPreview('')
    setHeroUrl('')
    notifyParent(menuItems, null)
  }

  // Add new menu item
  const addMenuItem = () => {
    const newItems = [...menuItems, { file: null, preview: '', url: '', name: '', price: '' }]
    setMenuItems(newItems)
  }

  // Remove menu item (completely removes from array)
  const removeMenuItem = (index: number) => {
    if (menuItems.length > 1) {
      const newItems = menuItems.filter((_, i) => i !== index)
      setMenuItems(newItems)
      notifyParent(newItems, heroUrl || null)
    }
  }

  // Clear image from menu item (keeps the item, just removes the image)
  const clearMenuImage = (index: number) => {
    const newItems = [...menuItems]
    newItems[index] = { ...newItems[index], file: null, preview: '', url: '' }
    setMenuItems(newItems)
    notifyParent(newItems, heroUrl || null)
  }

  const filledItemsCount = menuItems.filter(m => m.name || m.price || m.url).length
  const uploadedCount = (heroImage ? 1 : 0) + menuItems.filter(m => m.file !== null).length

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
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={heroPreview} alt="Hero" className="w-full h-32 object-cover rounded-lg" />
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
            <div className="py-6">
              <span className="text-3xl">🖼️</span>
              <p className="text-gray-500 mt-2 text-sm">Klik untuk muat naik gambar hero / Click to upload hero image</p>
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

      {/* MENU ITEMS - Unlimited */}
      <div>
        <label className="block text-sm font-medium mb-2">
          📷 Menu Produk (Unlimited)
        </label>
        <p className="text-xs text-gray-400 mb-3">
          Tambah gambar, nama dan harga untuk setiap item menu anda
        </p>

        <div className="space-y-3">
          {menuItems.map((item, index) => (
            <div key={index} className="flex gap-3 items-center p-4 bg-gray-50 rounded-xl border border-gray-200">
              {/* Image upload box */}
              <div
                className="w-20 h-20 border-2 border-dashed border-gray-300 rounded-lg flex-shrink-0 cursor-pointer hover:border-orange-400 transition flex items-center justify-center overflow-hidden"
                onClick={() => document.getElementById(`menu-upload-${index}`)?.click()}
              >
                {item.preview ? (
                  <div className="relative w-full h-full">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={item.preview}
                      alt={`Menu ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        clearMenuImage(index)
                      }}
                      className="absolute top-0 right-0 bg-red-500 text-white rounded-full w-5 h-5 text-xs hover:bg-red-600"
                      title="Remove image"
                    >✕</button>
                    {item.url && (
                      <div className="absolute bottom-0 left-0 right-0 bg-green-500 text-white text-xs text-center py-0.5">
                        ✓
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center">
                    <span className="text-2xl">📷</span>
                  </div>
                )}
                <input
                  id={`menu-upload-${index}`}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => handleMenuImageUpload(index, e)}
                  disabled={uploading}
                />
              </div>

              {/* Name & Price inputs */}
              <div className="flex-1 space-y-2">
                <input
                  type="text"
                  placeholder="Nama (cth: Nasi Lemak Special)"
                  value={item.name}
                  onChange={(e) => handleNameChange(index, e.target.value)}
                  className="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-transparent"
                />
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-600">RM</span>
                  <input
                    type="number"
                    placeholder="0.00"
                    step="0.50"
                    min="0"
                    value={item.price}
                    onChange={(e) => handlePriceChange(index, e.target.value)}
                    className="w-28 px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-orange-400 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Remove button */}
              {menuItems.length > 1 && (
                <button
                  onClick={() => removeMenuItem(index)}
                  className="text-red-500 hover:bg-red-50 p-2 rounded-full transition flex-shrink-0"
                  title="Buang item ini"
                >
                  🗑️
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Add more button */}
        <button
          onClick={addMenuItem}
          className="w-full mt-4 py-3 border-2 border-dashed border-orange-300 rounded-xl text-orange-600 font-medium hover:bg-orange-50 transition"
        >
          ➕ Tambah Item Lagi
        </button>

        {/* Item count */}
        <p className="text-sm text-gray-400 text-center mt-3">
          {filledItemsCount} item ditambah
        </p>
      </div>

      {/* Upload status */}
      <div className="mt-4 text-sm text-gray-500">
        ✅ {uploadedCount} gambar dimuat naik
      </div>
    </div>
  )
}

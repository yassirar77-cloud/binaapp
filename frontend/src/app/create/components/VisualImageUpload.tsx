'use client'

import { useState } from 'react'
import { API_BASE_URL } from '@/lib/env'
import { checkImageSafety } from '@/utils/imageModeration'

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
      // Moderation check before upload
      const moderationResult = await checkImageSafety(file)
      if (!moderationResult.allowed) {
        alert(moderationResult.message)
        return
      }

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
      // Moderation check before upload
      const moderationResult = await checkImageSafety(file)
      if (!moderationResult.allowed) {
        alert(moderationResult.message)
        return
      }

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
    <div className="cr-card cr-card-hairline" style={{ padding: '24px 28px', marginBottom: 20 }}>
      <div className="eyebrow" style={{ marginBottom: 16 }}>GAMBAR / IMAGES</div>
      <p style={{ fontSize: 13, color: '#86869A', marginBottom: 16 }}>
        Pilih gambar untuk setiap bahagian. Jika tidak muat naik, AI akan jana gambar automatik.
        <br />
        <span style={{ fontSize: 11, color: '#5A5A6E' }}>Choose images for each section. If not uploaded, AI will generate images automatically.</span>
      </p>

      {uploading && (
        <div style={{ marginBottom: 16, padding: 12, background: 'rgba(79,61,255,.06)', border: '1px solid rgba(107,92,255,.25)', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 16, height: 16, border: '2px solid rgba(107,92,255,.3)', borderTopColor: '#6B5CFF', borderRadius: '50%', animation: 'spin .6s linear infinite' }} />
          <span style={{ fontSize: 13, color: '#BAB0FF', fontWeight: 500 }}>{uploadProgress}</span>
        </div>
      )}

      {/* HERO IMAGE - Large Banner */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: '#B8B8C8', marginBottom: 8 }}>
          Gambar Utama (Hero Banner)
        </div>
        <p style={{ fontSize: 11, color: '#5A5A6E', marginBottom: 8 }}>Gambar besar di bahagian atas website / Large image at the top of the website</p>
        <div
          style={{ border: '2px dashed rgba(255,255,255,.08)', borderRadius: 14, padding: 16, textAlign: 'center', cursor: 'pointer', transition: 'border-color 180ms' }}
          onClick={() => document.getElementById('hero-upload')?.click()}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'rgba(107,92,255,.4)')}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,.08)')}
        >
          {heroPreview ? (
            <div style={{ position: 'relative' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={heroPreview} alt="Hero" style={{ width: '100%', height: 128, objectFit: 'cover', borderRadius: 10 }} />
              <button
                onClick={(e) => { e.stopPropagation(); removeHero(); }}
                style={{ position: 'absolute', top: 8, right: 8, width: 24, height: 24, borderRadius: '50%', background: 'rgba(239,68,68,.8)', border: 0, color: '#fff', fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                title="Remove image"
              >✕</button>
              {heroUrl && (
                <div style={{ position: 'absolute', bottom: 8, left: 8, background: 'rgba(199,255,61,.15)', border: '1px solid rgba(199,255,61,.3)', color: '#C7FF3D', fontSize: 11, padding: '2px 8px', borderRadius: 6, fontWeight: 600 }}>
                  ✓ Uploaded
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: '24px 0' }}>
              <span style={{ fontSize: 28, display: 'block', marginBottom: 8 }}>🖼️</span>
              <p style={{ fontSize: 13, color: '#86869A' }}>Klik untuk muat naik gambar hero / Click to upload hero image</p>
              <p style={{ fontSize: 11, color: '#5A5A6E', marginTop: 4 }}>Saiz dicadangkan / Recommended size: 1920 x 600 piksel</p>
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
        <div style={{ fontSize: 14, fontWeight: 500, color: '#B8B8C8', marginBottom: 8 }}>
          Menu Produk (Unlimited)
        </div>
        <p style={{ fontSize: 11, color: '#5A5A6E', marginBottom: 12 }}>
          Tambah gambar, nama dan harga untuk setiap item menu anda
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {menuItems.map((item, index) => (
            <div key={index} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: 14, background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 14 }}>
              {/* Image upload box */}
              <div
                style={{ width: 72, height: 72, border: '2px dashed rgba(255,255,255,.08)', borderRadius: 10, flexShrink: 0, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', transition: 'border-color 180ms' }}
                onClick={() => document.getElementById(`menu-upload-${index}`)?.click()}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'rgba(107,92,255,.4)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,.08)')}
              >
                {item.preview ? (
                  <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={item.preview}
                      alt={`Menu ${index + 1}`}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                    <button
                      onClick={(e) => { e.stopPropagation(); clearMenuImage(index); }}
                      style={{ position: 'absolute', top: 0, right: 0, width: 18, height: 18, borderRadius: '50%', background: 'rgba(239,68,68,.8)', border: 0, color: '#fff', fontSize: 10, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      title="Remove image"
                    >✕</button>
                    {item.url && (
                      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'rgba(199,255,61,.2)', color: '#C7FF3D', fontSize: 10, textAlign: 'center', padding: '1px 0', fontWeight: 700 }}>
                        ✓
                      </div>
                    )}
                  </div>
                ) : (
                  <span style={{ fontSize: 22, color: '#5A5A6E' }}>📷</span>
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
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <input
                  type="text"
                  placeholder="Nama (cth: Nasi Lemak Special)"
                  value={item.name}
                  onChange={(e) => handleNameChange(index, e.target.value)}
                  className="cr-input"
                  style={{ fontSize: 13, padding: '8px 12px' }}
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 500, color: '#86869A' }}>RM</span>
                  <input
                    type="number"
                    placeholder="0.00"
                    step="0.50"
                    min="0"
                    value={item.price}
                    onChange={(e) => handlePriceChange(index, e.target.value)}
                    className="cr-input"
                    style={{ width: 110, fontSize: 13, padding: '8px 12px' }}
                  />
                </div>
              </div>

              {/* Remove button */}
              {menuItems.length > 1 && (
                <button
                  onClick={() => removeMenuItem(index)}
                  style={{ padding: 8, borderRadius: '50%', border: 0, background: 'transparent', color: '#EF4444', cursor: 'pointer', flexShrink: 0, fontSize: 16, transition: 'background 180ms' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(239,68,68,.1)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
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
          style={{ width: '100%', marginTop: 14, padding: '12px 0', border: '2px dashed rgba(199,255,61,.2)', borderRadius: 14, background: 'transparent', color: '#C7FF3D', fontWeight: 500, fontSize: 13, cursor: 'pointer', transition: 'all 180ms', fontFamily: "'Geist', 'Inter', -apple-system, sans-serif" }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(199,255,61,.04)'; e.currentTarget.style.borderColor = 'rgba(199,255,61,.35)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(199,255,61,.2)'; }}
        >
          + Tambah Item Lagi
        </button>

        {/* Item count */}
        <p style={{ fontSize: 12, color: '#5A5A6E', textAlign: 'center', marginTop: 10 }}>
          {filledItemsCount} item ditambah
        </p>
      </div>

      {/* Upload status */}
      <div style={{ marginTop: 14, fontSize: 13, color: '#86869A' }}>
        <span style={{ color: '#C7FF3D' }}>✓</span> {uploadedCount} gambar dimuat naik
      </div>
    </div>
  )
}

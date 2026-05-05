'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useDropzone } from 'react-dropzone'
import { Upload, X, Image as ImageIcon, Camera } from 'lucide-react'
import ProgressBar from '../ProgressBar'
import { useOnboardingState, PhotoSlot } from '@/hooks/useOnboardingState'
import { supabase } from '@/lib/supabase'
import { getCurrentUser } from '@/lib/supabase'

type SlotKey = 'hero' | 'menu_1' | 'menu_2' | 'menu_3' | 'menu_4' | 'interior'

const SLOTS: { key: SlotKey; label: string; description: string; required: boolean }[] = [
  { key: 'hero', label: 'Foto Utama', description: 'Foto utama untuk laman web anda — pilih hidangan terbaik anda', required: true },
  { key: 'menu_1', label: 'Menu 1', description: 'Foto hidangan menu', required: false },
  { key: 'menu_2', label: 'Menu 2', description: 'Foto hidangan menu', required: false },
  { key: 'menu_3', label: 'Menu 3', description: 'Foto hidangan menu', required: false },
  { key: 'menu_4', label: 'Menu 4', description: 'Foto hidangan menu', required: false },
  { key: 'interior', label: 'Suasana', description: 'Foto suasana restoran anda (pilihan)', required: false },
]

const MAX_SIZE = 5 * 1024 * 1024 // 5MB
const MIN_WIDTH = 800
const MIN_HEIGHT = 600
const ACCEPTED = { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] }

function validateImage(file: File): Promise<string | null> {
  return new Promise(resolve => {
    if (file.size > MAX_SIZE) {
      resolve('Saiz fail melebihi 5MB')
      return
    }
    const img = new window.Image()
    img.onload = () => {
      if (img.width < MIN_WIDTH || img.height < MIN_HEIGHT) {
        resolve(`Gambar terlalu kecil (min ${MIN_WIDTH}×${MIN_HEIGHT})`)
      } else {
        resolve(null)
      }
    }
    img.onerror = () => resolve('Fail bukan gambar yang sah')
    img.src = URL.createObjectURL(file)
  })
}

interface SlotUploaderProps {
  slot: typeof SLOTS[number]
  photo: PhotoSlot | undefined
  uploading: boolean
  onUpload: (slot: SlotKey, file: File) => void
  onRemove: (slot: SlotKey) => void
}

function SlotUploader({ slot, photo, uploading, onUpload, onRemove }: SlotUploaderProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPTED,
    maxFiles: 1,
    onDrop: (files) => {
      if (files[0]) onUpload(slot.key, files[0])
    },
  })

  if (photo?.preview || photo?.url) {
    return (
      <div className="relative group rounded-xl overflow-hidden border-2 border-orange-200 aspect-[4/3]">
        <img
          src={photo.preview || photo.url}
          alt={slot.label}
          className="w-full h-full object-cover"
        />
        <button
          onClick={() => onRemove(slot.key)}
          className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <X size={16} />
        </button>
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-3">
          <p className="text-white text-sm font-medium">{slot.label}</p>
        </div>
      </div>
    )
  }

  return (
    <div
      {...getRootProps()}
      className={`relative rounded-xl border-2 border-dashed aspect-[4/3] flex flex-col items-center justify-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-orange-500 bg-orange-50'
          : 'border-gray-300 hover:border-orange-400 hover:bg-orange-50/50'
      } ${uploading ? 'pointer-events-none opacity-50' : ''}`}
    >
      <input {...getInputProps()} />
      {slot.key === 'hero' ? (
        <Camera size={32} className="text-orange-400 mb-2" />
      ) : (
        <ImageIcon size={28} className="text-gray-400 mb-2" />
      )}
      <p className="text-sm font-medium text-gray-700">{slot.label}</p>
      <p className="text-xs text-gray-500 mt-1 text-center px-2">{slot.description}</p>
      {isDragActive && (
        <p className="text-xs text-orange-600 mt-2">Lepaskan di sini</p>
      )}
    </div>
  )
}

export default function UploadPage() {
  const router = useRouter()
  const { state, setPhotos } = useOnboardingState()
  const [photos, setLocalPhotos] = useState<PhotoSlot[]>(state.photos)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const handleUpload = useCallback(async (slotKey: SlotKey, file: File) => {
    setError('')
    const validationError = await validateImage(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setUploading(true)
    try {
      const user = await getCurrentUser()
      const userId = user?.id || 'anonymous'
      const fileName = `${userId}/${slotKey}_${Date.now()}.${file.name.split('.').pop()}`

      const preview = URL.createObjectURL(file)

      let url = ''
      if (supabase) {
        const { data, error: uploadError } = await supabase.storage
          .from('restaurant-photos')
          .upload(fileName, file, { upsert: true })

        if (uploadError) {
          // If bucket doesn't exist, store preview only and flag
          console.warn('Supabase upload failed:', uploadError.message)
          url = preview // fallback to local preview
        } else {
          const { data: urlData } = supabase.storage
            .from('restaurant-photos')
            .getPublicUrl(fileName)
          url = urlData.publicUrl
        }
      } else {
        url = preview
      }

      const newPhoto: PhotoSlot = { file, url, preview, slot: slotKey }
      const updated = [...photos.filter(p => p.slot !== slotKey), newPhoto]
      setLocalPhotos(updated)
      setPhotos(updated)
    } catch (err) {
      console.error('Upload error:', err)
      setError('Gagal memuat naik. Sila cuba lagi.')
    } finally {
      setUploading(false)
    }
  }, [photos, setPhotos])

  const handleRemove = useCallback((slotKey: SlotKey) => {
    const updated = photos.filter(p => p.slot !== slotKey)
    setLocalPhotos(updated)
    setPhotos(updated)
  }, [photos, setPhotos])

  const hasPhotos = photos.length > 0
  const menuPhotos = photos.filter(p => p.slot.startsWith('menu_'))

  return (
    <>
      <ProgressBar currentStep={1} />

      <div className="text-center mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
          Muat Naik Foto Restoran Anda
        </h1>
        <p className="text-gray-600">
          Foto yang bagus = laman web yang cantik. Kami akan gunakan AI untuk cadangkan nama hidangan.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Hero slot - larger */}
      <div className="mb-6">
        <SlotUploader
          slot={SLOTS[0]}
          photo={photos.find(p => p.slot === 'hero')}
          uploading={uploading}
          onUpload={handleUpload}
          onRemove={handleRemove}
        />
      </div>

      {/* Menu slots grid */}
      <h3 className="text-lg font-semibold text-gray-800 mb-3">
        Foto Hidangan Menu
        <span className="text-sm font-normal text-gray-500 ml-2">
          — kami akan AI-suggest nama
        </span>
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {SLOTS.slice(1, 5).map(slot => (
          <SlotUploader
            key={slot.key}
            slot={slot}
            photo={photos.find(p => p.slot === slot.key)}
            uploading={uploading}
            onUpload={handleUpload}
            onRemove={handleRemove}
          />
        ))}
      </div>

      {/* Interior slot */}
      <h3 className="text-lg font-semibold text-gray-800 mb-3">
        Suasana Restoran
        <span className="text-sm font-normal text-gray-500 ml-2">(pilihan)</span>
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <SlotUploader
          slot={SLOTS[5]}
          photo={photos.find(p => p.slot === 'interior')}
          uploading={uploading}
          onUpload={handleUpload}
          onRemove={handleRemove}
        />
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <a
          href="/onboarding/dishes"
          className="text-sm text-gray-500 hover:text-gray-700 underline"
          onClick={(e) => {
            e.preventDefault()
            setPhotos([])
            router.push('/onboarding/dishes')
          }}
        >
          Langkau dan guna AI defaults
        </a>

        <button
          onClick={() => {
            setPhotos(photos)
            router.push('/onboarding/dishes')
          }}
          disabled={!hasPhotos || uploading}
          className="px-6 py-3 bg-orange-500 text-white font-semibold rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <Upload size={18} />
          Seterusnya — Hidangan
        </button>
      </div>
    </>
  )
}

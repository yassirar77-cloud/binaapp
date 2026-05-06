'use client'

import { Image as ImageIcon, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { Spinner } from '../primitives'
import { compressImage } from '../image-compression'
import { uploadDisputePhoto, PhotoUploadError } from '../dispute-api'

const MAX_PHOTOS = 3
const ACCEPTED_TYPES = 'image/jpeg,image/png,image/webp,image/heic,image/heif'

export interface DisputePhoto {
  /** Stable key for React lists. */
  id: string
  /** Local preview URL — object URL until upload completes. */
  previewUrl: string
  /** Public Supabase Storage URL once upload succeeds. */
  uploadedUrl: string | null
  uploading: boolean
  error: string | null
}

interface PhotoUploadProps {
  orderNumber: string
  photos: DisputePhoto[]
  onChange: (next: DisputePhoto[]) => void
}

/**
 * Optional 3-photo grid uploader. Each tile compresses → uploads →
 * shows progress → falls back to retry-on-error. The submit button
 * waits for in-flight uploads via `photos.some(p => p.uploading)`.
 *
 * Photos beyond MAX_PHOTOS are silently rejected with a toast.
 */
export function PhotoUpload({ orderNumber, photos, onChange }: PhotoUploadProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  // Keep a ref to the latest photos so async upload callbacks read the
  // current state instead of capturing the value at scheduling time.
  const photosRef = useRef(photos)
  useEffect(() => {
    photosRef.current = photos
  }, [photos])

  const updatePhoto = (id: string, patch: Partial<DisputePhoto>) => {
    onChange(
      photosRef.current.map((p) => (p.id === id ? { ...p, ...patch } : p))
    )
  }

  const removePhoto = (id: string) => {
    const target = photosRef.current.find((p) => p.id === id)
    if (target?.previewUrl) {
      URL.revokeObjectURL(target.previewUrl)
    }
    onChange(photosRef.current.filter((p) => p.id !== id))
  }

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const slotsLeft = MAX_PHOTOS - photosRef.current.length
    if (slotsLeft <= 0) {
      toast(`Maksimum ${MAX_PHOTOS} gambar`)
      return
    }

    const toProcess = Array.from(files).slice(0, slotsLeft)
    if (files.length > slotsLeft) {
      toast(`Maksimum ${MAX_PHOTOS} gambar`)
    }

    const validFiles = toProcess.filter((f) => f.type.startsWith('image/'))
    if (validFiles.length < toProcess.length) {
      toast('Sila pilih fail gambar sahaja')
    }

    // Append placeholder tiles synchronously so the user sees something.
    const placeholders = validFiles.map((f) => ({
      id: cryptoId(),
      previewUrl: URL.createObjectURL(f),
      uploadedUrl: null as string | null,
      uploading: true,
      error: null as string | null,
      file: f,
    }))
    const initial: DisputePhoto[] = placeholders.map(({ file: _f, ...rest }) => rest)
    onChange([...photosRef.current, ...initial])

    // Compress + upload each in sequence.
    for (const ph of placeholders) {
      try {
        const compressed = await compressImage(ph.file)
        const url = await uploadDisputePhoto(compressed.blob, orderNumber)
        updatePhoto(ph.id, { uploadedUrl: url, uploading: false, error: null })
      } catch (err) {
        const msg =
          err instanceof PhotoUploadError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Muat naik gagal'
        updatePhoto(ph.id, { uploading: false, error: msg })
      }
    }
  }

  const empties = MAX_PHOTOS - photos.length

  return (
    <div className="dp-sec">
      <h3>
        Lampirkan gambar
        <span className="opt">(pilihan, max {MAX_PHOTOS})</span>
      </h3>
      <div className="photo-grid">
        {photos.map((p) => (
          <div
            key={p.id}
            className="photo-tile has-img"
            style={{ backgroundImage: `url(${p.previewUrl})` }}
          >
            {p.uploading && (
              <div className="progress" aria-live="polite">
                <Spinner />
                <span>Memuat naik…</span>
              </div>
            )}
            {p.error && (
              <div className="err-overlay" role="alert">
                {p.error}
              </div>
            )}
            {!p.uploading && (
              <button
                type="button"
                className="rmv"
                onClick={() => removePhoto(p.id)}
                aria-label="Buang gambar"
              >
                <X size={11} strokeWidth={2.4} aria-hidden="true" />
              </button>
            )}
          </div>
        ))}
        {empties > 0 && (
          <button
            type="button"
            className="photo-tile"
            onClick={() => inputRef.current?.click()}
            aria-label="Tambah gambar"
          >
            <ImageIcon size={20} strokeWidth={1.8} aria-hidden="true" />
            <span className="lbl">Tambah gambar</span>
          </button>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        multiple
        capture="environment"
        hidden
        onChange={(e) => {
          handleFiles(e.target.files)
          // Reset so the same file can be re-picked after a failed upload.
          if (inputRef.current) inputRef.current.value = ''
        }}
      />
      <div className="photo-hint">
        Tip: gambar membantu restoran faham masalah dengan cepat.
      </div>
    </div>
  )
}

function cryptoId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
}

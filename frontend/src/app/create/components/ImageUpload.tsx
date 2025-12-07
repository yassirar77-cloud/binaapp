'use client'

import { useState } from 'react'

interface ImageUploadProps {
  onImagesUploaded: (urls: string[]) => void
}

export default function ImageUpload({ onImagesUploaded }: ImageUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [images, setImages] = useState<string[]>([])

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files) return

    setUploading(true)
    const uploadedUrls: string[] = []

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const formData = new FormData()
      formData.append('file', file)

      try {
        const res = await fetch('http://localhost:8000/api/upload-image', {
          method: 'POST',
          body: formData
        })

        const data = await res.json()

        if (data.success) {
          uploadedUrls.push(data.url)
        }
      } catch (error) {
        console.error('Upload failed:', error)
      }
    }

    const allImages = [...images, ...uploadedUrls]
    setImages(allImages)
    setUploading(false)
    onImagesUploaded(allImages)
  }

  return (
    <div style={{
      padding: '30px',
      background: '#f9fafb',
      borderRadius: '15px',
      marginBottom: '20px'
    }}>
      <h3 style={{ marginBottom: '15px', fontSize: '20px', fontWeight: 'bold' }}>
        📸 Upload Food Photos
      </h3>
      <p style={{ color: '#666', marginBottom: '20px', fontSize: '14px' }}>
        Add photos of your menu items to make your website more attractive
      </p>

      <input
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileChange}
        style={{
          padding: '10px',
          border: '2px dashed #667eea',
          borderRadius: '8px',
          width: '100%',
          cursor: 'pointer',
          background: 'white'
        }}
      />

      {uploading && (
        <p style={{ marginTop: '15px', color: '#667eea', fontWeight: 'bold' }}>
          ⏳ Uploading images...
        </p>
      )}

      {images.length > 0 && (
        <div style={{
          marginTop: '20px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
          gap: '15px'
        }}>
          {images.map((url, i) => (
            <div key={i} style={{
              position: 'relative',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '2px solid #e5e7eb'
            }}>
              <img
                src={url}
                alt={`Upload ${i+1}`}
                style={{
                  width: '100%',
                  height: '150px',
                  objectFit: 'cover'
                }}
              />
              <p style={{
                padding: '5px',
                fontSize: '12px',
                textAlign: 'center',
                background: 'white',
                margin: 0
              }}>
                Photo {i+1}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

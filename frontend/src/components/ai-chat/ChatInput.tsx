'use client'

import React, { useState, useRef, useCallback } from 'react'

interface ChatInputProps {
  onSend: (message: string, imageUrls: string[]) => void
  onUploadImage: (file: File) => Promise<string>
  disabled?: boolean
  placeholder?: string
}

export default function ChatInput({
  onSend,
  onUploadImage,
  disabled = false,
  placeholder = 'Taip mesej anda...',
}: ChatInputProps) {
  const [text, setText] = useState('')
  const [pendingImages, setPendingImages] = useState<{ file: File; preview: string; url?: string }[]>([])
  const [uploading, setUploading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }, [])

  const handleSend = async () => {
    const trimmed = text.trim()
    if (!trimmed && pendingImages.length === 0) return
    if (disabled || uploading) return

    // Upload any pending images
    const imageUrls: string[] = []
    if (pendingImages.length > 0) {
      setUploading(true)
      for (const img of pendingImages) {
        if (img.url) {
          imageUrls.push(img.url)
        } else {
          try {
            const url = await onUploadImage(img.file)
            imageUrls.push(url)
          } catch {
            // Skip failed uploads
          }
        }
      }
      setUploading(false)
    }

    onSend(trimmed || '(gambar)', imageUrls)
    setText('')
    setPendingImages([])
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    const newImages: { file: File; preview: string }[] = []
    for (let i = 0; i < Math.min(files.length, 3); i++) {
      const file = files[i]
      if (file.size > 5 * 1024 * 1024) continue
      if (!file.type.startsWith('image/')) continue

      newImages.push({
        file,
        preview: URL.createObjectURL(file),
      })
    }

    setPendingImages((prev) => [...prev, ...newImages].slice(0, 3))
    e.target.value = ''
  }

  const removeImage = (index: number) => {
    setPendingImages((prev) => {
      const updated = [...prev]
      URL.revokeObjectURL(updated[index].preview)
      updated.splice(index, 1)
      return updated
    })
  }

  const canSend = (text.trim().length > 0 || pendingImages.length > 0) && !disabled && !uploading

  return (
    <div className="border-t bg-white">
      {/* Image previews */}
      {pendingImages.length > 0 && (
        <div className="flex gap-2 px-4 pt-3">
          {pendingImages.map((img, i) => (
            <div key={i} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={img.preview}
                alt={`Preview ${i + 1}`}
                className="w-16 h-16 object-cover rounded-lg border"
              />
              <button
                onClick={() => removeImage(i)}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 p-3">
        {/* Image upload */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || pendingImages.length >= 3}
          className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-40 transition-colors"
          title="Muat naik gambar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <polyline points="21 15 16 10 5 21"/>
          </svg>
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Text input */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value)
            adjustTextareaHeight()
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none border border-gray-200 rounded-2xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400 disabled:opacity-50 max-h-[120px]"
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={!canSend}
          className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? (
            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" strokeOpacity="0.25"/>
              <path d="M4 12a8 8 0 018-8" strokeLinecap="round"/>
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}

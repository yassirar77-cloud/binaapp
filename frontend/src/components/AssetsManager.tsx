'use client';

import { useState, useCallback } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

interface AssetsManagerProps {
  onLogoChange: (url: string | null) => void;
  onImagesChange: (urls: string[]) => void;
  onFontsChange: (fonts: string[]) => void;
  logo: string | null;
  images: string[];
  fonts: string[];
}

export default function AssetsManager({ onLogoChange, onImagesChange, onFontsChange, logo, images, fonts }: AssetsManagerProps) {
  const supabase = createClientComponentClient();
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState<string | null>(null);
  const [fontInput, setFontInput] = useState('');

  const uploadFile = async (file: File, type: 'logo' | 'image'): Promise<string | null> => {
    try {
      const fileName = `${Date.now()}-${file.name.replace(/[^a-zA-Z0-9.]/g, '_')}`;
      const { data, error } = await supabase.storage.from('assets').upload(fileName, file);

      if (error) {
        console.error('Upload error:', error);
        return null;
      }

      return `${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/assets/${fileName}`;
    } catch (err) {
      console.error('Upload failed:', err);
      return null;
    }
  };

  const handleDrop = useCallback(async (e: React.DragEvent, type: 'logo' | 'images') => {
    e.preventDefault();
    setDragOver(null);

    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
    if (files.length === 0) return;

    setUploading(true);

    if (type === 'logo') {
      const url = await uploadFile(files[0], 'logo');
      if (url) onLogoChange(url);
    } else {
      const newUrls: string[] = [];
      for (const file of files) {
        const url = await uploadFile(file, 'image');
        if (url) newUrls.push(url);
      }
      onImagesChange([...images, ...newUrls]);
    }

    setUploading(false);
  }, [images, onLogoChange, onImagesChange]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>, type: 'logo' | 'images') => {
    const files = e.target.files;
    if (!files) return;

    setUploading(true);

    if (type === 'logo') {
      const url = await uploadFile(files[0], 'logo');
      if (url) onLogoChange(url);
    } else {
      const newUrls: string[] = [];
      for (const file of Array.from(files)) {
        const url = await uploadFile(file, 'image');
        if (url) newUrls.push(url);
      }
      onImagesChange([...images, ...newUrls]);
    }

    setUploading(false);
    e.target.value = '';
  };

  const removeImage = (index: number) => {
    onImagesChange(images.filter((_, i) => i !== index));
  };

  const addFont = () => {
    if (fontInput.trim() && !fonts.includes(fontInput.trim())) {
      onFontsChange([...fonts, fontInput.trim()]);
      setFontInput('');
    }
  };

  const removeFont = (index: number) => {
    onFontsChange(fonts.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-gray-800 mb-1">🎨 Brand Assets</h2>
        <p className="text-sm text-gray-500">Upload logos, fonts, and images for AI to use</p>
      </div>

      {/* Logo Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">✨</span>
          <h3 className="font-semibold text-gray-700">Logo</h3>
        </div>
        <div
          onDrop={(e) => handleDrop(e, 'logo')}
          onDragOver={(e) => { e.preventDefault(); setDragOver('logo'); }}
          onDragLeave={() => setDragOver(null)}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer
            ${dragOver === 'logo' ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
        >
          {logo ? (
            <div className="relative inline-block">
              <img src={logo} alt="Logo" className="max-h-20 mx-auto rounded" />
              <button
                onClick={(e) => { e.stopPropagation(); onLogoChange(null); }}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 text-xs font-bold hover:bg-red-600"
              >
                ×
              </button>
            </div>
          ) : (
            <label className="cursor-pointer block">
              <div className="text-3xl mb-2">⬆️</div>
              <p className="text-gray-600 font-medium">Drag & drop logo files</p>
              <p className="text-gray-400 text-sm">or click to browse</p>
              <input type="file" accept="image/*" onChange={(e) => handleFileSelect(e, 'logo')} className="hidden" />
            </label>
          )}
        </div>
      </div>

      {/* Fonts Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔤</span>
          <h3 className="font-semibold text-gray-700">Fonts</h3>
          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full text-gray-600">{fonts.length}</span>
        </div>

        <div className="space-y-2">
          {fonts.map((font, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-gray-700" style={{ fontFamily: font }}>Aa</span>
                <div>
                  <span className="text-gray-700 font-medium">{font}</span>
                  <span className="text-xs text-green-600 ml-2">✓ Google Fonts</span>
                </div>
              </div>
              <button onClick={() => removeFont(i)} className="text-gray-400 hover:text-red-500 text-xl">×</button>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={fontInput}
            onChange={(e) => setFontInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addFont()}
            placeholder="Font name or Google Fonts URL"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button onClick={addFont} className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium">
            + Add
          </button>
        </div>
        <p className="text-xs text-gray-400">
          e.g., "Inter" or "Poppins" - <a href="https://fonts.google.com" target="_blank" className="text-blue-500 hover:underline">View Google Fonts</a>
        </p>
      </div>

      {/* Images Section */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🖼️</span>
          <h3 className="font-semibold text-gray-700">Images</h3>
          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full text-gray-600">{images.length}</span>
        </div>

        <div
          onDrop={(e) => handleDrop(e, 'images')}
          onDragOver={(e) => { e.preventDefault(); setDragOver('images'); }}
          onDragLeave={() => setDragOver(null)}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition-all
            ${dragOver === 'images' ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
        >
          <label className="cursor-pointer block">
            <div className="text-3xl mb-2">⬆️</div>
            <p className="text-gray-600 font-medium">Upload images</p>
            <p className="text-gray-400 text-sm">Drag & drop or click to browse</p>
            <input type="file" accept="image/*" multiple onChange={(e) => handleFileSelect(e, 'images')} className="hidden" />
          </label>
        </div>

        {images.length > 0 && (
          <div className="grid grid-cols-3 gap-2 mt-3">
            {images.map((img, i) => (
              <div key={i} className="relative group aspect-square">
                <img src={img} alt={`Asset ${i + 1}`} className="w-full h-full object-cover rounded-lg" />
                <button
                  onClick={() => removeImage(i)}
                  className="absolute top-1 right-1 bg-red-500 text-white rounded-full w-5 h-5 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  ×
                </button>
                <div className="absolute bottom-1 left-1 bg-black/50 text-white text-xs px-1.5 py-0.5 rounded">
                  {i === 0 ? 'Hero' : `Image ${i}`}
                </div>
              </div>
            ))}
          </div>
        )}
        <p className="text-xs text-gray-400">Upload images for AI to use in your website. First image = Hero.</p>
      </div>

      {/* Uploading Overlay */}
      {uploading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-xl">
            <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
            <p className="mt-3 text-gray-600 font-medium">Uploading...</p>
          </div>
        </div>
      )}
    </div>
  );
}

'use client';

import { useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';

interface Assets {
  logo: string | null;
  images: string[];
  fonts: string[];
  colors: {
    primary: string;
    secondary: string;
    accent: string;
  };
}

interface AssetsManagerProps {
  assets: Assets;
  onAssetsChange: (assets: Assets) => void;
}

export default function AssetsManager({ assets, onAssetsChange }: AssetsManagerProps) {
  const [uploading, setUploading] = useState(false);

  const handleDrop = useCallback(async (e: React.DragEvent, type: 'logo' | 'images') => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    setUploading(true);
    try {
      for (const file of files) {
        const fileName = `${Date.now()}-${file.name}`;
        const { data, error } = await supabase.storage
          .from('assets')
          .upload(fileName, file);

        if (data) {
          const { data: { publicUrl } } = supabase.storage
            .from('assets')
            .getPublicUrl(fileName);

          if (type === 'logo') {
            onAssetsChange({ ...assets, logo: publicUrl });
          } else {
            onAssetsChange({ ...assets, images: [...assets.images, publicUrl] });
          }
        }
      }
    } catch (err) {
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  }, [assets, onAssetsChange]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>, type: 'logo' | 'images') => {
    const files = e.target.files;
    if (!files) return;

    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const fileName = `${Date.now()}-${file.name}`;
        const { data } = await supabase.storage
          .from('assets')
          .upload(fileName, file);

        if (data) {
          const { data: { publicUrl } } = supabase.storage
            .from('assets')
            .getPublicUrl(fileName);

          if (type === 'logo') {
            onAssetsChange({ ...assets, logo: publicUrl });
          } else {
            onAssetsChange({ ...assets, images: [...assets.images, publicUrl] });
          }
        }
      }
    } catch (err) {
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  const removeImage = (index: number) => {
    const newImages = assets.images.filter((_, i) => i !== index);
    onAssetsChange({ ...assets, images: newImages });
  };

  const addFont = (fontName: string) => {
    if (!assets.fonts.includes(fontName)) {
      onAssetsChange({ ...assets, fonts: [...assets.fonts, fontName] });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-gray-800 mb-1">🎨 Brand Assets</h2>
        <p className="text-sm text-gray-500">Upload logos, fonts, and images for AI to use</p>
      </div>

      {/* Logo Section */}
      <div className="space-y-3">
        <h3 className="font-semibold text-gray-700 flex items-center gap-2">
          <span>✨</span> Logo
        </h3>
        <div
          onDrop={(e) => handleDrop(e, 'logo')}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors cursor-pointer"
        >
          {assets.logo ? (
            <div className="relative inline-block">
              <img src={assets.logo} alt="Logo" className="max-h-24 mx-auto" />
              <button
                onClick={() => onAssetsChange({ ...assets, logo: null })}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 text-xs hover:bg-red-600"
              >
                ×
              </button>
            </div>
          ) : (
            <>
              <div className="text-4xl mb-2">⬆️</div>
              <p className="text-gray-500">Drag & drop logo here</p>
              <p className="text-gray-400 text-sm">or click to browse</p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleFileSelect(e, 'logo')}
                className="hidden"
                id="logo-upload"
              />
              <label htmlFor="logo-upload" className="cursor-pointer text-blue-500 text-sm mt-2 inline-block hover:underline">
                Browse files
              </label>
            </>
          )}
        </div>
      </div>

      {/* Fonts Section */}
      <div className="space-y-3">
        <h3 className="font-semibold text-gray-700 flex items-center gap-2">
          <span>🔤</span> Fonts
          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">{assets.fonts.length}</span>
        </h3>
        <div className="space-y-2">
          {assets.fonts.map((font, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold" style={{ fontFamily: font }}>Aa</span>
                <span className="text-gray-700">{font}</span>
              </div>
              <button
                onClick={() => onAssetsChange({ ...assets, fonts: assets.fonts.filter((_, idx) => idx !== i) })}
                className="text-gray-400 hover:text-red-500"
              >
                ×
              </button>
            </div>
          ))}
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g., Inter, Poppins, Roboto"
              className="flex-1 px-3 py-2 border rounded-lg text-sm"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  const value = (e.target as HTMLInputElement).value.trim();
                  if (value) {
                    addFont(value);
                    (e.target as HTMLInputElement).value = '';
                  }
                }
              }}
            />
            <button
              onClick={() => {
                const input = document.querySelector('input[placeholder*="Inter"]') as HTMLInputElement;
                if (input && input.value.trim()) {
                  addFont(input.value.trim());
                  input.value = '';
                }
              }}
              className="px-3 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200"
            >
              + Add
            </button>
          </div>
          <p className="text-xs text-gray-400">
            Press Enter or click Add - <a href="https://fonts.google.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">Browse Google Fonts</a>
          </p>
        </div>
      </div>

      {/* Images Section */}
      <div className="space-y-3">
        <h3 className="font-semibold text-gray-700 flex items-center gap-2">
          <span>🖼️</span> Images
          <span className="text-xs bg-gray-100 px-2 py-0.5 rounded-full">{assets.images.length}</span>
        </h3>
        <div
          onDrop={(e) => handleDrop(e, 'images')}
          onDragOver={(e) => e.preventDefault()}
          className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors cursor-pointer"
        >
          <div className="text-3xl mb-2">⬆️</div>
          <p className="text-gray-500">Drag & drop images here</p>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => handleFileSelect(e, 'images')}
            className="hidden"
            id="images-upload"
          />
          <label htmlFor="images-upload" className="cursor-pointer text-blue-500 text-sm hover:underline">
            or click to browse
          </label>
        </div>

        {assets.images.length > 0 && (
          <div className="grid grid-cols-3 gap-3 mt-4">
            {assets.images.map((img, i) => (
              <div key={i} className="relative group">
                <img src={img} alt={`Asset ${i}`} className="w-full h-20 object-cover rounded-lg" />
                <button
                  onClick={() => removeImage(i)}
                  className="absolute top-1 right-1 bg-red-500 text-white rounded-full w-5 h-5 text-xs opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        <p className="text-xs text-gray-400">Upload images for AI to use in your website</p>
      </div>

      {/* Color Scheme */}
      <div className="space-y-3">
        <h3 className="font-semibold text-gray-700 flex items-center gap-2">
          <span>🎨</span> Color Scheme
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Primary</label>
            <input
              type="color"
              value={assets.colors.primary}
              onChange={(e) => onAssetsChange({ ...assets, colors: { ...assets.colors, primary: e.target.value } })}
              className="w-full h-10 rounded cursor-pointer"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Secondary</label>
            <input
              type="color"
              value={assets.colors.secondary}
              onChange={(e) => onAssetsChange({ ...assets, colors: { ...assets.colors, secondary: e.target.value } })}
              className="w-full h-10 rounded cursor-pointer"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Accent</label>
            <input
              type="color"
              value={assets.colors.accent}
              onChange={(e) => onAssetsChange({ ...assets, colors: { ...assets.colors, accent: e.target.value } })}
              className="w-full h-10 rounded cursor-pointer"
            />
          </div>
        </div>
      </div>

      {uploading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-xl">
            <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
            <p className="mt-3 text-gray-600">Uploading...</p>
          </div>
        </div>
      )}
    </div>
  );
}

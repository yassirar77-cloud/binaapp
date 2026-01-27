'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import { User } from '@supabase/supabase-js';
import AssetsManager from '@/components/AssetsManager';
import { detectTheme, Theme } from '@/lib/themeDetector';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

interface Assets {
  logo: string | null;
  images: string[];
  fonts: string[];
  colors: { primary: string; secondary: string; accent: string; };
}

export default function CreatePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  const [activeTab, setActiveTab] = useState<'build' | 'assets'>('build');
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [html, setHtml] = useState('');
  const [theme, setTheme] = useState<Theme | null>(null);
  const [components, setComponents] = useState<string[]>([]);
  const [assets, setAssets] = useState<Assets>({
    logo: null,
    images: [],
    fonts: ['Inter', 'Poppins'],
    colors: { primary: '#3b82f6', secondary: '#f1f5f9', accent: '#8b5cf6' }
  });
  const [viewMode, setViewMode] = useState<'desktop' | 'mobile'>('desktop');

  useEffect(() => {
    checkUser();
  }, []);

  useEffect(() => {
    if (prompt.length > 10) {
      const detected = detectTheme(prompt);
      setTheme(detected);
      // Auto-update colors based on theme
      setAssets(prev => ({
        ...prev,
        colors: {
          primary: detected.colors.primary,
          secondary: detected.colors.secondary,
          accent: detected.colors.accent
        },
        fonts: [detected.fonts.heading, detected.fonts.body]
      }));
    }
  }, [prompt]);

  async function checkUser() {
    if (!supabase) return;
    try {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleGenerate() {
    if (!prompt.trim()) return;

    setGenerating(true);
    setComponents([]);
    setHtml('');

    try {
      // Show progress
      setComponents(['🎨 Initializing project theme: ' + (theme?.name || 'Custom')]);
      await new Promise(r => setTimeout(r, 500));

      setComponents(prev => [...prev, '🔍 Analyzing business type...']);
      await new Promise(r => setTimeout(r, 500));

      setComponents(prev => [...prev, `📝 Adding font '${assets.fonts[0] || 'Inter'}'`]);
      await new Promise(r => setTimeout(r, 300));

      if (assets.fonts[1]) {
        setComponents(prev => [...prev, `📝 Adding font '${assets.fonts[1]}'`]);
        await new Promise(r => setTimeout(r, 300));
      }

      if (assets.logo) {
        setComponents(prev => [...prev, '🖼️ Using uploaded logo']);
        await new Promise(r => setTimeout(r, 300));
      }

      if (assets.images.length > 0) {
        setComponents(prev => [...prev, `📷 Using ${assets.images.length} uploaded images`]);
        await new Promise(r => setTimeout(r, 300));
      }

      setComponents(prev => [...prev, '🤖 Generating HTML with AI...']);

      // Call API with assets
      const response = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: prompt,
          images: assets.images,
          logo: assets.logo,
          fonts: assets.fonts,
          colors: assets.colors,
          theme: theme?.name,
          multi_style: false
        })
      });

      const data = await response.json();

      if (data.html) {
        setComponents(prev => [...prev, '✅ Creating component "HomePage"']);
        await new Promise(r => setTimeout(r, 500));
        setHtml(data.html);
        setComponents(prev => [...prev, '✅ Website generated successfully!']);
      }
    } catch (err) {
      console.error(err);
      setComponents(prev => [...prev, '❌ Error generating website']);
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave() {
    if (!supabase) return;

    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      router.push('/login');
      return;
    }

    const subdomain = prompt.split(' ')[0].toLowerCase().replace(/[^a-z0-9]/g, '');

    // Save to database
    const { data, error } = await supabase
      .from('websites')
      .insert({
        user_id: session.user.id,
        name: prompt.split(' ').slice(0, 3).join(' '),
        subdomain,
        description: prompt,
        html_content: html,
        template: theme?.name || 'custom',
        status: 'draft'
      })
      .select()
      .single();

    if (data) {
      // Upload to storage
      await supabase.storage
        .from('websites')
        .upload(`${subdomain}/index.html`, new Blob([html], { type: 'text/html' }), { upsert: true });

      alert('✅ Website saved!');
      router.push('/my-projects');
    } else {
      alert('❌ Error saving: ' + error?.message);
    }
  }

  async function handleLogout() {
    if (!supabase) return;
    await supabase.auth.signOut();
    router.push('/');
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <Link href="/my-projects" className="text-sm text-gray-600 hover:text-gray-900">
                  My Projects
                </Link>
                <button onClick={handleLogout} className="text-sm text-red-500 hover:text-red-600">
                  Logout
                </button>
              </>
            ) : (
              <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">
                Login
              </Link>
            )}
          </div>
        </nav>
      </header>

      <div className="flex-1 flex">
        {/* Left Sidebar */}
        <div className="w-80 bg-white border-r flex flex-col">
          {/* Tabs */}
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('build')}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${
                activeTab === 'build'
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              🔨 Build
            </button>
            <button
              onClick={() => setActiveTab('assets')}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${
                activeTab === 'assets'
                  ? 'border-b-2 border-blue-500 text-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              🎨 Assets
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === 'build' ? (
              <div className="space-y-4">
                {/* Theme Detection */}
                {theme && (
                  <div className="p-3 bg-gradient-to-r from-orange-50 to-amber-50 rounded-lg border border-orange-200">
                    <div className="flex items-center gap-2 text-sm mb-1">
                      <span>🎨</span>
                      <span className="font-medium text-orange-700">{theme.name}</span>
                    </div>
                    <p className="text-xs text-orange-600">{theme.description}</p>
                    <div className="flex gap-2 mt-2">
                      <div className="w-6 h-6 rounded" style={{ backgroundColor: theme.colors.primary }}></div>
                      <div className="w-6 h-6 rounded" style={{ backgroundColor: theme.colors.secondary }}></div>
                      <div className="w-6 h-6 rounded" style={{ backgroundColor: theme.colors.accent }}></div>
                    </div>
                  </div>
                )}

                {/* Progress */}
                {components.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-gray-700">Build Progress:</h3>
                    {components.map((comp, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
                        <span className="mt-0.5">{comp.includes('✅') ? '✅' : comp.includes('❌') ? '❌' : '⏳'}</span>
                        <span className="flex-1">{comp.replace(/^[✅❌⏳🎨🔍📝🖼️📷🤖]\s*/, '')}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Prompt Input */}
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-2">
                    What do you want to build?
                  </label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Saya ada kedai kucing bernama 'Purrfect Paws' di Kuala Lumpur..."
                    rows={6}
                    className="w-full p-3 border rounded-lg text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <div className="text-xs text-gray-500 mt-1">{prompt.length} characters</div>
                </div>

                {/* Generate Button */}
                <button
                  onClick={handleGenerate}
                  disabled={generating || !prompt.trim()}
                  className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 hover:from-blue-600 hover:to-purple-600 transition-all"
                >
                  {generating ? (
                    <>
                      <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                      Generating...
                    </>
                  ) : (
                    <>✨ Generate Website</>
                  )}
                </button>

                {/* Save Button */}
                {html && (
                  <button
                    onClick={handleSave}
                    className="w-full py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                  >
                    💾 Save & Publish
                  </button>
                )}
              </div>
            ) : (
              <AssetsManager assets={assets} onAssetsChange={setAssets} />
            )}
          </div>
        </div>

        {/* Right Canvas */}
        <div className="flex-1 flex flex-col bg-gray-100">
          {/* Canvas Header */}
          <div className="bg-white border-b px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">📐 Design Canvas</span>
              {theme && (
                <span className="text-xs bg-gray-100 px-2 py-1 rounded">{theme.name}</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('desktop')}
                className={`p-2 rounded hover:bg-gray-100 ${viewMode === 'desktop' ? 'bg-gray-200' : ''}`}
                title="Desktop view"
              >
                🖥️
              </button>
              <button
                onClick={() => setViewMode('mobile')}
                className={`p-2 rounded hover:bg-gray-100 ${viewMode === 'mobile' ? 'bg-gray-200' : ''}`}
                title="Mobile view"
              >
                📱
              </button>
            </div>
          </div>

          {/* Canvas Preview */}
          <div className="flex-1 p-6 overflow-auto">
            <div
              className={`bg-white rounded-lg shadow-2xl mx-auto transition-all duration-300 ${
                viewMode === 'desktop' ? 'max-w-6xl' : 'max-w-sm'
              }`}
              style={{ minHeight: '600px' }}
            >
              {html ? (
                <iframe
                  srcDoc={html}
                  className="w-full rounded-lg"
                  style={{ height: '800px' }}
                  title="Preview"
                  sandbox="allow-scripts allow-same-origin"
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400">
                  <div className="text-center p-8">
                    <div className="text-6xl mb-4">🎨</div>
                    <p className="text-lg font-medium mb-2">Ready to create?</p>
                    <p className="text-sm">Enter your business description in the Build tab</p>
                    <p className="text-sm mt-2">Upload assets in the Assets tab</p>
                    <p className="text-sm mt-4 text-gray-500">
                      Your website preview will appear here
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

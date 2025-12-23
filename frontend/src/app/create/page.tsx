'use client';

import { useState, useEffect } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { useRouter } from 'next/navigation';
import AssetsManager from '@/components/AssetsManager';
import ProgressIndicator from '@/components/ProgressIndicator';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

interface Step {
  text: string;
  status: 'pending' | 'loading' | 'done' | 'error';
}

export default function CreatePage() {
  const router = useRouter();
  const supabase = createClientComponentClient();

  const [activeTab, setActiveTab] = useState<'build' | 'assets'>('build');
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [html, setHtml] = useState('');
  const [theme, setTheme] = useState('');
  const [steps, setSteps] = useState<Step[]>([]);
  const [viewMode, setViewMode] = useState<'desktop' | 'mobile'>('desktop');

  // Assets state
  const [logo, setLogo] = useState<string | null>(null);
  const [images, setImages] = useState<string[]>([]);
  const [fonts, setFonts] = useState<string[]>(['Poppins', 'Inter']);

  // Detect theme from prompt
  useEffect(() => {
    if (prompt.length < 10) return;
    const p = prompt.toLowerCase();

    if (p.includes('kucing') || p.includes('cat') || p.includes('pet')) {
      setTheme('🐱 Purrfect Paws Theme');
    } else if (p.includes('salon') || p.includes('rambut') || p.includes('beauty')) {
      setTheme('💇 Glamour Beauty Theme');
    } else if (p.includes('makan') || p.includes('restoran') || p.includes('food')) {
      setTheme('🍽️ Tasty Bites Theme');
    } else if (p.includes('pakaian') || p.includes('fashion') || p.includes('clothing')) {
      setTheme('👗 Fashion Forward Theme');
    } else {
      setTheme('✨ Professional Theme');
    }
  }, [prompt]);

  const addStep = (text: string, status: Step['status'] = 'loading') => {
    setSteps(prev => [...prev, { text, status }]);
  };

  const updateLastStep = (status: Step['status']) => {
    setSteps(prev => {
      const newSteps = [...prev];
      if (newSteps.length > 0) {
        newSteps[newSteps.length - 1].status = status;
      }
      return newSteps;
    });
  };

  async function handleGenerate() {
    if (!prompt.trim()) return;

    setGenerating(true);
    setSteps([]);
    setHtml('');

    try {
      addStep(`Initializing project theme: ${theme}`);
      await new Promise(r => setTimeout(r, 600));
      updateLastStep('done');

      addStep('Analyzing business type...');
      await new Promise(r => setTimeout(r, 400));
      updateLastStep('done');

      if (fonts.length > 0) {
        addStep(`Adding font '${fonts[0]}'`);
        await new Promise(r => setTimeout(r, 300));
        updateLastStep('done');
      }

      if (images.length > 0) {
        addStep(`Processing ${images.length} uploaded image(s)`);
        await new Promise(r => setTimeout(r, 300));
        updateLastStep('done');
      }

      addStep('Creating component "HomePage"');

      const response = await fetch(`${API_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_description: prompt,
          images: images,
          logo: logo,
          fonts: fonts,
          multi_style: false
        })
      });

      const data = await response.json();

      if (data.html || data.styles?.[0]?.html) {
        updateLastStep('done');
        addStep('Generating styles and components');
        await new Promise(r => setTimeout(r, 500));
        updateLastStep('done');

        setHtml(data.html || data.styles[0].html);
        addStep('✅ Website generated successfully!');
        updateLastStep('done');
      } else {
        updateLastStep('error');
        addStep('❌ Failed to generate website');
        updateLastStep('error');
      }
    } catch (err) {
      console.error(err);
      updateLastStep('error');
      addStep('❌ Error occurred');
      updateLastStep('error');
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave() {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      router.push('/login');
      return;
    }

    const subdomain = prompt.split(' ')[0].toLowerCase().replace(/[^a-z0-9]/g, '') || 'mysite';
    const name = prompt.split(' ').slice(0, 4).join(' ') || 'My Website';

    const { data, error } = await supabase
      .from('websites')
      .insert({
        user_id: session.user.id,
        name,
        subdomain,
        description: prompt,
        html_content: html,
        assets: { logo, images, fonts }
      })
      .select()
      .single();

    if (data) {
      await supabase.storage
        .from('websites')
        .upload(`${subdomain}/index.html`, new Blob([html], { type: 'text/html' }), { upsert: true });

      alert('✅ Website saved!');
      router.push('/my-projects');
    } else {
      alert('Error saving: ' + error?.message);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Left Sidebar */}
      <div className="w-80 bg-white border-r flex flex-col">
        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => setActiveTab('build')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'build'
                ? 'border-b-2 border-blue-500 text-blue-600 bg-blue-50/50'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            🔨 Build
          </button>
          <button
            onClick={() => setActiveTab('assets')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'assets'
                ? 'border-b-2 border-blue-500 text-blue-600 bg-blue-50/50'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            🎨 Assets
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'build' ? (
            <div className="space-y-4">
              {/* Progress */}
              {steps.length > 0 && (
                <ProgressIndicator steps={steps} theme={theme} />
              )}

              {/* Theme Badge */}
              {theme && steps.length === 0 && (
                <div className="p-3 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-purple-700">{theme}</span>
                  </div>
                </div>
              )}

              {/* Prompt Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">What do you want to build?</label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="e.g., kedai kucing pet shop in Penang with grooming services"
                  rows={4}
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={generating || !prompt.trim()}
                className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-medium disabled:opacity-50 flex items-center justify-center gap-2 hover:from-blue-600 hover:to-purple-600 transition-all"
              >
                {generating ? (
                  <>
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
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

              {/* Assets Summary */}
              {(logo || images.length > 0) && (
                <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
                  <p className="font-medium mb-1">Assets attached:</p>
                  {logo && <p>• 1 logo</p>}
                  {images.length > 0 && <p>• {images.length} image(s)</p>}
                  {fonts.length > 0 && <p>• {fonts.length} font(s)</p>}
                </div>
              )}
            </div>
          ) : (
            <AssetsManager
              logo={logo}
              images={images}
              fonts={fonts}
              onLogoChange={setLogo}
              onImagesChange={setImages}
              onFontsChange={setFonts}
            />
          )}
        </div>
      </div>

      {/* Right Canvas */}
      <div className="flex-1 flex flex-col">
        {/* Canvas Header */}
        <div className="bg-white border-b px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-medium text-gray-700">📐 Design Canvas</span>
          </div>
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('desktop')}
              className={`px-3 py-1.5 rounded-md text-sm transition-all ${viewMode === 'desktop' ? 'bg-white shadow text-gray-800' : 'text-gray-500'}`}
            >
              🖥️ Desktop
            </button>
            <button
              onClick={() => setViewMode('mobile')}
              className={`px-3 py-1.5 rounded-md text-sm transition-all ${viewMode === 'mobile' ? 'bg-white shadow text-gray-800' : 'text-gray-500'}`}
            >
              📱 Mobile
            </button>
          </div>
        </div>

        {/* Canvas Preview */}
        <div className="flex-1 bg-gray-100 p-6 overflow-auto flex justify-center">
          <div
            className={`bg-white rounded-xl shadow-2xl overflow-hidden transition-all duration-300 ${
              viewMode === 'mobile' ? 'w-[375px]' : 'w-full max-w-5xl'
            }`}
          >
            {html ? (
              <iframe
                srcDoc={html}
                className={`w-full border-0 ${viewMode === 'mobile' ? 'h-[667px]' : 'h-[800px]'}`}
                title="Website Preview"
              />
            ) : (
              <div className="h-[600px] flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <div className="text-6xl mb-4">🎨</div>
                  <p className="text-lg font-medium">Describe your business</p>
                  <p className="text-sm mt-2">Your website preview will appear here</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

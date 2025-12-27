'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import AIEditor from './AIEditor';

interface Website {
  id: string;
  name: string;
  subdomain: string | null;
  html_content: string | null;
  user_id: string;
}

export default function EditorPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [website, setWebsite] = useState<Website | null>(null);
  const [html, setHtml] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWebsite();
  }, [id]);

  async function loadWebsite() {
    if (!supabase) {
      setError('Supabase tidak tersedia');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);

      // Check if user is authenticated
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }

      // Fetch website data
      const { data, error } = await supabase
        .from('websites')
        .select('*')
        .eq('id', id)
        .eq('user_id', session.user.id)
        .single();

      if (error || !data) {
        setError('Website tidak dijumpai');
        setTimeout(() => router.push('/my-projects'), 2000);
        return;
      }

      setWebsite(data);
      setHtml(data.html_content || '');
    } catch (e) {
      console.error('Error loading website:', e);
      setError('Ralat memuatkan website');
    } finally {
      setLoading(false);
    }
  }

  async function saveWebsite() {
    if (!supabase || !website) return;

    setSaving(true);
    try {
      // Update database
      const { error } = await supabase
        .from('websites')
        .update({
          html_content: html,
          updated_at: new Date().toISOString()
        })
        .eq('id', id);

      if (error) throw error;

      // If website has subdomain and is published, update storage
      if (website.subdomain) {
        try {
          const blob = new Blob([html], { type: 'text/html' });
          const { error: storageError } = await supabase.storage
            .from('websites')
            .upload(`${website.subdomain}/index.html`, blob, {
              upsert: true,
              contentType: 'text/html'
            });

          if (storageError) {
            console.error('Storage update error:', storageError);
            // Don't fail the save if storage update fails
          }
        } catch (storageErr) {
          console.error('Storage error:', storageErr);
          // Continue even if storage update fails
        }
      }

      alert('✅ Berjaya disimpan!');
    } catch (e) {
      console.error('Error saving:', e);
      alert('❌ Ralat menyimpan. Sila cuba lagi.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Memuatkan editor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">{error}</h1>
          <p className="text-gray-500 mb-4">Mengalihkan ke senarai projek...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex-1">
            <h1 className="text-lg font-bold text-gray-800">{website?.name || 'Editor'}</h1>
            {website?.subdomain && (
              <p className="text-sm text-gray-500">{website.subdomain}.binaapp.my</p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push('/my-projects')}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              ← Kembali
            </button>
            <button
              onClick={saveWebsite}
              disabled={saving}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? '💾 Menyimpan...' : '💾 Simpan'}
            </button>
          </div>
        </div>
      </div>

      {/* Editor Container */}
      <div className="flex-1 flex flex-col p-4 gap-4 overflow-y-auto">
        {/* AI Editor Section */}
        <div className="w-full">
          <AIEditor
            html={html}
            onHtmlChange={(newHtml) => setHtml(newHtml)}
          />
        </div>

        {/* Code Editor and Preview Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1">
          {/* Code Editor */}
          <div className="flex flex-col border rounded-xl overflow-hidden shadow-sm bg-white">
            <div className="bg-gray-100 px-4 py-2 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700">📝 HTML Editor</h2>
            </div>
            <textarea
              value={html}
              onChange={(e) => setHtml(e.target.value)}
              className="flex-1 w-full p-4 font-mono text-sm border-0 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Masukkan kod HTML anda di sini..."
              spellCheck={false}
            />
          </div>

          {/* Preview */}
          <div className="flex flex-col border rounded-xl overflow-hidden shadow-sm bg-white">
            <div className="bg-gray-100 px-4 py-2 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-700">👁 Preview</h2>
            </div>
            <div className="flex-1 overflow-auto">
              <iframe
                srcDoc={html}
                className="w-full h-full border-0"
                title="Website Preview"
                sandbox="allow-scripts allow-same-origin allow-forms"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Notice */}
      <div className="lg:hidden bg-yellow-50 border-t border-yellow-200 p-3 text-center">
        <p className="text-sm text-yellow-800">
          💡 Untuk pengalaman terbaik, gunakan komputer atau tablet dalam mod landscape
        </p>
      </div>
    </div>
  );
}

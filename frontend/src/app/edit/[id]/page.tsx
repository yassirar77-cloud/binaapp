'use client';

import { useState, useEffect } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { useRouter, useParams } from 'next/navigation';

export default function EditWebsitePage() {
  const params = useParams();
  const websiteId = params.id;
  const router = useRouter();
  const supabase = createClientComponentClient();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [website, setWebsite] = useState<any>(null);
  const [htmlContent, setHtmlContent] = useState('');
  // Per-website analytics opt-out (migration 038). Default to true so a
  // website created before this column existed (NULL in older rows) keeps
  // analytics on until the merchant explicitly opts out.
  const [analyticsEnabled, setAnalyticsEnabled] = useState(true);
  const [analyticsToggling, setAnalyticsToggling] = useState(false);

  useEffect(() => {
    loadWebsite();
  }, [websiteId]);

  async function loadWebsite() {
    try {
      const { data, error } = await supabase
        .from('websites')
        .select('*')
        .eq('id', websiteId)
        .single();

      if (error) throw error;

      setWebsite(data);
      setHtmlContent(data.html_content || '');
      setAnalyticsEnabled(data.analytics_enabled !== false);
    } catch (error) {
      console.error('Error loading website:', error);
      alert('Website tidak dijumpai');
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  }

  // Immediate-save toggle. Optimistically flips local state, persists to
  // Supabase, reverts on error. Separate from the Simpan button so the
  // privacy choice isn't held hostage by unsaved HTML edits.
  async function toggleAnalytics(next: boolean) {
    if (analyticsToggling) return;
    const previous = analyticsEnabled;
    setAnalyticsEnabled(next);
    setAnalyticsToggling(true);
    try {
      const { error } = await supabase
        .from('websites')
        .update({
          analytics_enabled: next,
          updated_at: new Date().toISOString(),
        })
        .eq('id', websiteId);
      if (error) throw error;
    } catch (error) {
      console.error('Error toggling analytics:', error);
      alert('Ralat menyimpan tetapan analitis. Sila cuba lagi.');
      setAnalyticsEnabled(previous);
    } finally {
      setAnalyticsToggling(false);
    }
  }

  async function saveWebsite() {
    try {
      setSaving(true);

      const { error } = await supabase
        .from('websites')
        .update({
          html_content: htmlContent,
          updated_at: new Date().toISOString()
        })
        .eq('id', websiteId);

      if (error) throw error;

      // Also update in Supabase storage
      const { data: { user } } = await supabase.auth.getUser();
      if (user && website.subdomain) {
        await supabase.storage
          .from('websites')
          .upload(`${website.subdomain}/index.html`, htmlContent, {
            contentType: 'text/html',
            upsert: true
          });
      }

      alert('Website berjaya disimpan!');
    } catch (error) {
      console.error('Error saving:', error);
      alert('Ralat menyimpan website');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-4 py-3 flex justify-between items-center">
        <div>
          <h1 className="font-bold text-lg">Edit: {website?.name}</h1>
          <p className="text-sm text-gray-500">{website?.subdomain}.binaapp.my</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => router.push('/dashboard')}
            className="px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            Batal
          </button>
          <button
            onClick={saveWebsite}
            disabled={saving}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            {saving ? 'Menyimpan...' : 'Simpan'}
          </button>
        </div>
      </div>

      {/* Privacy toggle — immediate-save, separate from HTML save */}
      <div className="bg-white border-b px-4 py-3 flex items-start gap-3">
        <label className="flex items-center gap-2 shrink-0 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={analyticsEnabled}
            disabled={analyticsToggling}
            onChange={(e) => toggleAnalytics(e.target.checked)}
            className="w-4 h-4 accent-blue-600 cursor-pointer disabled:cursor-wait"
          />
          <span className="text-sm font-medium text-gray-900">
            Aktifkan analitis pelawat
          </span>
        </label>
        <p className="text-xs text-gray-500 leading-relaxed pt-0.5">
          Track page views, devices, dan referrers untuk laman web ini. Tiada
          data dijual atau dikongsi dengan pihak ketiga. Matikan untuk
          membuang skrip pengesanan BinaApp dari HTML laman web ini.
          {analyticsToggling && <span className="ml-2 text-gray-400">(menyimpan…)</span>}
        </p>
      </div>

      {/* Editor */}
      <div className="flex h-[calc(100vh-108px)]">
        {/* Code Editor */}
        <div className="w-1/2 border-r">
          <textarea
            value={htmlContent}
            onChange={(e) => setHtmlContent(e.target.value)}
            className="w-full h-full p-4 font-mono text-sm resize-none focus:outline-none"
            placeholder="HTML code here..."
          />
        </div>

        {/* Preview */}
        <div className="w-1/2">
          <iframe
            srcDoc={htmlContent}
            className="w-full h-full border-0"
            title="Preview"
          />
        </div>
      </div>
    </div>
  );
}

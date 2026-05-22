'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { supabase, getCurrentUser, getStoredToken } from '@/lib/supabase';
import { buildRegenerateWarning } from '@/lib/regenerateWarning';
import AIEditor from './AIEditor';

// Backend API URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

interface Website {
  id: string;
  name?: string;
  business_name?: string;
  subdomain: string | null;
  html_content: string | null;
  user_id: string;
  description?: string | null;
  generation_count?: number | null;
  status?: string;
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

  // Regenerate state. `pendingDescription` is the textarea value the
  // user can tweak before kicking off another generation; it starts off
  // empty so the placeholder hints they can leave it blank to reuse the
  // stored one. `regenerating` is true while the backend job is running
  // (we poll GET /:id every 3s waiting for status to leave 'generating').
  const [pendingDescription, setPendingDescription] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);
  const [regenerateError, setRegenerateError] = useState<string | null>(null);
  // Count of menu_items with image_url for this website — drives the
  // image-aware warning + acknowledge checkbox inside the confirm modal.
  // Defaults to 0 (= soft warning, no checkbox) until the fetch resolves
  // so an in-flight count doesn't pop the strong warning incorrectly.
  const [uploadedImageCount, setUploadedImageCount] = useState(0);
  // Checkbox tick state inside the modal. Reset every time the modal is
  // opened so a previous "I understand" tick can't carry over.
  const [acknowledgeReplace, setAcknowledgeReplace] = useState(false);

  useEffect(() => {
    loadWebsite();
    loadUploadedImageCount();
  }, [id]);

  // Fetch the number of menu_items with a non-empty image_url for this
  // website. Used by the regenerate confirm modal to decide whether to
  // show the strong "photos will be replaced" warning. Failures are
  // swallowed (count stays at 0) — falling back to the soft warning is
  // safer than blocking the modal entirely.
  async function loadUploadedImageCount() {
    try {
      const url = `${API_BASE}/api/v1/websites/${id}/menu-items`;
      const customToken = getStoredToken();
      const headers: Record<string, string> = {};
      if (customToken) headers['Authorization'] = `Bearer ${customToken}`;
      const resp = await fetch(url, { headers });
      if (!resp.ok) return;
      const items = await resp.json();
      if (!Array.isArray(items)) return;
      const count = items.filter(
        (it: { image_url?: string | null }) =>
          typeof it?.image_url === 'string' && it.image_url.trim().length > 0
      ).length;
      setUploadedImageCount(count);
    } catch (err) {
      console.warn('Failed to fetch uploaded image count:', err);
    }
  }

  async function loadWebsite() {
    try {
      setLoading(true);

      // First check for custom BinaApp token
      const customToken = getStoredToken();
      const customUser = await getCurrentUser();

      if (customToken && customUser) {
        console.log('[Editor] ✅ Using custom BinaApp auth');

        // Fetch website using backend API
        const response = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
          headers: {
            'Authorization': `Bearer ${customToken}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.status === 401) {
          router.push('/login');
          return;
        }

        if (response.ok) {
          const data = await response.json();
          setWebsite(data);
          setHtml(data.html_content || '');
        } else {
          setError('Website tidak dijumpai');
          setTimeout(() => router.push('/dashboard'), 2000);
        }
        return;
      }

      // Fallback to Supabase session
      if (!supabase) {
        setError('Sila log masuk');
        router.push('/login');
        return;
      }

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }

      // Fetch website data using Supabase
      const { data, error } = await supabase
        .from('websites')
        .select('*')
        .eq('id', id)
        .eq('user_id', session.user.id)
        .single();

      if (error || !data) {
        setError('Website tidak dijumpai');
        setTimeout(() => router.push('/dashboard'), 2000);
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
    if (!website) return;

    setSaving(true);
    try {
      // First try using custom BinaApp token
      const customToken = getStoredToken();

      if (customToken) {
        // Use backend API for custom auth users
        const response = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${customToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            html_content: html
          })
        });

        if (response.ok) {
          alert('✅ Berjaya disimpan!');
          return;
        } else if (response.status === 401) {
          // Token expired, redirect to login
          router.push('/login');
          return;
        } else {
          throw new Error('Failed to save via API');
        }
      }

      // Fallback to Supabase for legacy users
      if (!supabase) {
        alert('❌ Sila log masuk semula.');
        router.push('/login');
        return;
      }

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

  async function regenerateWebsite() {
    if (!website) return;
    setRegenerateError(null);

    const customToken = getStoredToken();
    if (!customToken) {
      // Regenerate is gated on the backend's custom-auth JWT — we don't
      // expose the same endpoint on the supabase-session fallback path.
      setRegenerateError('Sila log masuk semula untuk meneruskan.');
      return;
    }

    setRegenerating(true);

    try {
      const body: Record<string, string> = {};
      const trimmed = pendingDescription.trim();
      if (trimmed.length > 0) {
        body.description = trimmed;
      }

      const response = await fetch(
        `${API_BASE}/api/v1/websites/${id}/regenerate`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${customToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        }
      );

      if (response.status === 401) {
        router.push('/login');
        return;
      }

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        const detail = errBody?.detail;
        // Backend returns either a string detail or an object with
        // {error, message, ...}. Surface whichever we have.
        if (typeof detail === 'string') {
          setRegenerateError(detail);
        } else if (detail?.message) {
          setRegenerateError(detail.message);
        } else {
          setRegenerateError('Ralat regenerate. Sila cuba lagi.');
        }
        setRegenerating(false);
        return;
      }

      // Poll GET /:id until status leaves 'generating'. Backend marks
      // the row as 'generating' immediately and flips to 'draft' (or
      // 'failed') when the background AI task finishes. Cap at ~5min
      // so a stuck job doesn't loop forever.
      const maxAttempts = 100; // 100 * 3s = 5 minutes
      let attempt = 0;
      const poll = setInterval(async () => {
        attempt += 1;
        if (attempt > maxAttempts) {
          clearInterval(poll);
          setRegenerating(false);
          setRegenerateError(
            'Regenerate mengambil masa terlalu lama. Sila refresh halaman.'
          );
          return;
        }
        try {
          const statusResp = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
            headers: { Authorization: `Bearer ${customToken}` },
          });
          if (!statusResp.ok) return;
          const data = await statusResp.json();
          if (data.status === 'generating') return;
          clearInterval(poll);
          setWebsite(data);
          setHtml(data.html_content || '');
          setPendingDescription('');
          setRegenerating(false);
          if (data.status === 'failed') {
            setRegenerateError(
              'Regenerate gagal. AI tidak dapat menjana laman web. Sila cuba lagi.'
            );
          }
        } catch (pollErr) {
          console.warn('Poll error:', pollErr);
        }
      }, 3000);
    } catch (e) {
      console.error('Regenerate error:', e);
      setRegenerateError('Ralat regenerate. Sila cuba lagi.');
      setRegenerating(false);
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
            <h1 className="text-lg font-bold text-gray-800">{website?.business_name || website?.name || 'Editor'}</h1>
            {website?.subdomain && (
              <p className="text-sm text-gray-500">{website.subdomain}.binaapp.my</p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push('/dashboard')}
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
        {/* Regenerate Section — edit the AI prompt + re-run generation. */}
        <div className="w-full bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3 mb-3">
            <div>
              <h2 className="text-base font-bold text-gray-800">
                🪄 Regenerate dengan AI
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Edit penerangan kemudian regenerate. HTML semasa akan
                digantikan dengan versi baru.
                {typeof website?.generation_count === 'number' && (
                  <span className="ml-1 text-gray-400">
                    (sudah regenerate {Math.max(0, website.generation_count - 1)}x)
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Current stored description, read-only context */}
          {website?.description && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-3">
              <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Penerangan semasa
              </div>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">
                {website.description}
              </p>
            </div>
          )}

          <label className="block text-xs font-semibold text-gray-700 mb-1.5">
            Penerangan baru{' '}
            <span className="font-normal text-gray-400">
              (kosongkan untuk guna semula yang asal)
            </span>
          </label>
          <textarea
            value={pendingDescription}
            onChange={(e) => setPendingDescription(e.target.value)}
            disabled={regenerating}
            rows={3}
            maxLength={5000}
            placeholder={
              website?.description
                ? 'Biarkan kosong untuk guna semula penerangan asal…'
                : 'Tuliskan penerangan baru (minimum 10 huruf)…'
            }
            className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:cursor-not-allowed resize-vertical"
          />

          {regenerateError && (
            <div className="mt-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
              {regenerateError}
            </div>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setAcknowledgeReplace(false);
                setShowRegenerateConfirm(true);
              }}
              disabled={
                regenerating ||
                (!website?.description && pendingDescription.trim().length < 10)
              }
              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {regenerating ? '⏳ Regenerating…' : '🪄 Regenerate Website'}
            </button>
            {regenerating && (
              <span className="text-xs text-gray-500">
                AI sedang menjana laman web baru. Ini mengambil 1–3 minit.
              </span>
            )}
          </div>
        </div>

        {/* Regenerate confirm modal */}
        {showRegenerateConfirm && (
          <RegenerateConfirmModal
            uploadedImageCount={uploadedImageCount}
            acknowledgeReplace={acknowledgeReplace}
            onAcknowledgeChange={setAcknowledgeReplace}
            onCancel={() => setShowRegenerateConfirm(false)}
            onConfirm={() => {
              setShowRegenerateConfirm(false);
              regenerateWebsite();
            }}
          />
        )}

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

interface RegenerateConfirmModalProps {
  uploadedImageCount: number;
  acknowledgeReplace: boolean;
  onAcknowledgeChange: (next: boolean) => void;
  onCancel: () => void;
  onConfirm: () => void;
}

function RegenerateConfirmModal({
  uploadedImageCount,
  acknowledgeReplace,
  onAcknowledgeChange,
  onCancel,
  onConfirm,
}: RegenerateConfirmModalProps) {
  const warning = useMemo(
    () => buildRegenerateWarning(uploadedImageCount),
    [uploadedImageCount]
  );
  const confirmDisabled = warning.requiresAcknowledge && !acknowledgeReplace;
  // Screen-reader announcement for the disabled state — without it the
  // button just goes silent when the checkbox is unticked.
  const disabledReason =
    confirmDisabled
      ? 'Tick the acknowledgement checkbox to enable this button.'
      : '';

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="regenerate-confirm-title"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3
          id="regenerate-confirm-title"
          className="text-lg font-bold text-gray-900 mb-2"
        >
          {warning.headline}
        </h3>
        <p
          className={`text-sm mb-4 ${
            warning.hasUploadedImages ? 'text-red-700' : 'text-gray-600'
          }`}
        >
          {warning.body}
        </p>

        {warning.requiresAcknowledge && (
          <label className="flex items-start gap-2 mb-4 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={acknowledgeReplace}
              onChange={(e) => onAcknowledgeChange(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
              aria-describedby="regenerate-ack-help"
            />
            <span
              id="regenerate-ack-help"
              className="text-sm text-gray-800"
            >
              {warning.checkboxLabel}
            </span>
          </label>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Batal
          </button>
          <button
            onClick={onConfirm}
            disabled={confirmDisabled}
            aria-disabled={confirmDisabled}
            aria-describedby={confirmDisabled ? 'regenerate-confirm-help' : undefined}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Ya, regenerate
          </button>
        </div>
        {confirmDisabled && (
          <p
            id="regenerate-confirm-help"
            className="sr-only"
            role="status"
            aria-live="polite"
          >
            {disabledReason}
          </p>
        )}
      </div>
    </div>
  );
}

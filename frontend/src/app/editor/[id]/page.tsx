'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import toast from 'react-hot-toast';
import {
  supabase,
  getCurrentUser,
  getStoredToken,
  getApiAuthToken,
} from '@/lib/supabase';
import { buildRegenerateWarning } from '@/lib/regenerateWarning';
import {
  STYLE_CHIPS,
  applyStyleChip,
  chipIsStillApplied,
  type StyleChipId,
} from '@/lib/regenerateStyleChips';
import { detectIntent, type IntentResult } from '@/lib/aiAssistantIntent';
import { pollMessageForElapsed } from '@/lib/regeneratePollMessages';

// Backend API URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

// Prefill suggestions under the prompt box. The first two route to a
// quick edit, the last two to a full regenerate — a deliberate mix so
// the user sees both kinds of outcome.
const QUICK_SUGGESTIONS = [
  'Tukar warna jadi merah',
  'Tambah nombor telefon',
  'Buat lagi modern',
  'Dark theme',
] as const;

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

function mapQuickEditError(code?: string): string {
  switch (code) {
    case 'Timeout - cuba lagi':
      return 'Timeout - cuba lagi dalam beberapa saat.';
    case 'No API key':
      return 'AI tidak dikonfigurasi. Sila hubungi sokongan.';
    case 'Missing data':
      return 'Data tidak lengkap. Cuba lagi.';
    case 'Unauthorized':
      return 'Sila log masuk semula.';
    default:
      return 'Gagal. Cuba lagi.';
  }
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

  // Unified AI Assistant state. `prompt` is the single source of truth
  // for everything the user wants to do — `detectIntent` decides whether
  // it's a quick edit or a full regenerate.
  const [prompt, setPrompt] = useState('');
  const [applying, setApplying] = useState(false);
  const [assistantMode, setAssistantMode] = useState<
    'quick_edit' | 'full_regenerate' | null
  >(null);
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const [pollText, setPollText] = useState('');

  // Full-regenerate confirm modal (photo-replacement warning). Only the
  // full_regenerate path opens it — quick edits run immediately.
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);
  const [uploadedImageCount, setUploadedImageCount] = useState(0);
  const [acknowledgeReplace, setAcknowledgeReplace] = useState(false);

  // Selected style hint chip (single-select; composes the prompt text).
  const [selectedChipId, setSelectedChipId] = useState<StyleChipId | null>(null);

  // True when a quick edit changed the in-memory html but it hasn't been
  // saved yet. Drives the unsaved-changes guard. A full regenerate is
  // persisted server-side, so it does NOT set this flag.
  const [dirty, setDirty] = useState(false);

  // Poll bookkeeping kept in refs so the unmount cleanup can clear the
  // interval and the elapsed-time message stays stable across renders.
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollStartRef = useRef<number>(0);
  const pollErrorsRef = useRef<number>(0);

  const detected: IntentResult | null = useMemo(() => {
    const t = prompt.trim();
    return t.length > 0 ? detectIntent(t) : null;
  }, [prompt]);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    loadWebsite();
    loadUploadedImageCount();
  }, [id]);

  // Memory-leak fix: clear any running poll interval when the component
  // unmounts. Without this, navigating away mid-regenerate left the
  // 3s interval running and calling setState on an unmounted component.
  useEffect(() => {
    return () => stopPolling();
  }, []);

  // Warn before leaving (tab close / refresh) when there are unsaved
  // quick-edit changes. Browsers show their own generic prompt here.
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

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

      const customToken = getStoredToken();
      const customUser = await getCurrentUser();

      if (customToken && customUser) {
        const response = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
          headers: {
            Authorization: `Bearer ${customToken}`,
            'Content-Type': 'application/json',
          },
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

      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }

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
      const customToken = getStoredToken();

      if (customToken) {
        const response = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${customToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ html_content: html }),
        });

        if (response.ok) {
          setDirty(false);
          toast.success('✓ Tersimpan', { duration: 2000 });
          return;
        } else if (response.status === 401) {
          router.push('/login');
          return;
        } else {
          throw new Error('Failed to save via API');
        }
      }

      // Fallback to Supabase for legacy users
      if (!supabase) {
        toast.error('Sila log masuk semula.');
        router.push('/login');
        return;
      }

      const { error } = await supabase
        .from('websites')
        .update({
          html_content: html,
          updated_at: new Date().toISOString(),
        })
        .eq('id', id);

      if (error) throw error;

      if (website.subdomain) {
        try {
          const blob = new Blob([html], { type: 'text/html' });
          const { error: storageError } = await supabase.storage
            .from('websites')
            .upload(`${website.subdomain}/index.html`, blob, {
              upsert: true,
              contentType: 'text/html',
            });
          if (storageError) {
            console.error('Storage update error:', storageError);
          }
        } catch (storageErr) {
          console.error('Storage error:', storageErr);
        }
      }

      setDirty(false);
      toast.success('✓ Tersimpan', { duration: 2000 });
    } catch (e) {
      console.error('Error saving:', e);
      toast.error('Ralat menyimpan. Sila cuba lagi.');
    } finally {
      setSaving(false);
    }
  }

  // Entry point for the single "Laksanakan" button. Routes to the right
  // backend based on detected intent.
  function applyChanges() {
    if (!website || applying) return;
    setAssistantError(null);
    const result = detectIntent(prompt);
    if (result.intent === 'quick_edit') {
      runQuickEdit();
    } else {
      setAcknowledgeReplace(false);
      setShowRegenerateConfirm(true);
    }
  }

  // Quick edit: POST /api/edit-website (proxies to /api/edit-html) WITH
  // an auth token. Updates the in-memory html only — not persisted until
  // the user hits Simpan, so we mark the buffer dirty.
  async function runQuickEdit() {
    const token = await getApiAuthToken();
    if (!token) {
      const msg = 'Sila log masuk semula untuk meneruskan.';
      setAssistantError(msg);
      toast.error(msg);
      return;
    }

    setApplying(true);
    setAssistantMode('quick_edit');
    const instruction = prompt.trim();
    try {
      const response = await fetch('/api/edit-website', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ html, instruction }),
      });

      if (response.status === 401) {
        router.push('/login');
        return;
      }

      const data = await response.json().catch(() => ({}));
      if (response.ok && data?.success && data?.html) {
        setHtml(data.html);
        setDirty(true);
        setPrompt('');
        setSelectedChipId(null);
        toast.success('Perubahan dibuat. Tekan Simpan untuk kekal.');
      } else {
        const msg = mapQuickEditError(data?.error);
        setAssistantError(msg);
        toast.error(msg);
      }
    } catch (e) {
      console.error('Quick edit error:', e);
      const msg = 'Ralat rangkaian. Cuba lagi.';
      setAssistantError(msg);
      toast.error(msg);
    } finally {
      setApplying(false);
      setAssistantMode(null);
    }
  }

  // Full regenerate: PATCH /regenerate then poll GET /:id until status
  // leaves 'generating'. The job is persisted server-side, so this does
  // NOT mark the buffer dirty.
  async function runRegenerate() {
    if (!website) return;
    setAssistantError(null);

    const token = await getApiAuthToken();
    if (!token) {
      const msg = 'Sila log masuk semula untuk meneruskan.';
      setAssistantError(msg);
      toast.error(msg);
      return;
    }

    setApplying(true);
    setAssistantMode('full_regenerate');
    pollStartRef.current = Date.now();
    pollErrorsRef.current = 0;
    setPollText(pollMessageForElapsed(0));

    try {
      const body: Record<string, string> = {};
      const trimmed = prompt.trim();
      if (trimmed.length > 0) body.description = trimmed;

      const response = await fetch(
        `${API_BASE}/api/v1/websites/${id}/regenerate`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
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
        let msg = 'Ralat regenerate. Sila cuba lagi.';
        if (typeof detail === 'string') msg = detail;
        else if (detail?.message) msg = detail.message;
        setAssistantError(msg);
        toast.error(msg);
        setApplying(false);
        setAssistantMode(null);
        return;
      }

      // Poll until the background AI task finishes. Cap at ~5min so a
      // stuck job doesn't loop forever. Interval id is stored in a ref
      // so unmount can cancel it.
      const maxAttempts = 100; // 100 * 3s = 5 minutes
      let attempt = 0;
      stopPolling();
      pollRef.current = setInterval(async () => {
        attempt += 1;
        setPollText(pollMessageForElapsed(Date.now() - pollStartRef.current));

        if (attempt > maxAttempts) {
          stopPolling();
          setApplying(false);
          setAssistantMode(null);
          const msg =
            'Regenerate mengambil masa terlalu lama. Sila refresh halaman.';
          setAssistantError(msg);
          toast.error(msg);
          return;
        }

        try {
          const statusResp = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          if (!statusResp.ok) {
            // Tolerate a few transient blips, then give up so the
            // button isn't stranded in the "applying" state forever.
            pollErrorsRef.current += 1;
            if (pollErrorsRef.current >= 3) {
              stopPolling();
              setApplying(false);
              setAssistantMode(null);
              const msg = 'Gagal menyemak status. Sila cuba lagi.';
              setAssistantError(msg);
              toast.error(msg);
            }
            return;
          }

          pollErrorsRef.current = 0;
          const data = await statusResp.json();
          if (data.status === 'generating') return;

          stopPolling();
          setWebsite(data);
          setHtml(data.html_content || '');
          setPrompt('');
          setSelectedChipId(null);
          setApplying(false);
          setAssistantMode(null);

          if (data.status === 'failed') {
            const msg =
              'Regenerate gagal. AI tidak dapat menjana laman web. Sila cuba lagi.';
            setAssistantError(msg);
            toast.error(msg);
          } else {
            toast.success('Website baru siap. Tekan Simpan untuk kekal.');
          }
        } catch (pollErr) {
          console.warn('Poll error:', pollErr);
          pollErrorsRef.current += 1;
          if (pollErrorsRef.current >= 3) {
            stopPolling();
            setApplying(false);
            setAssistantMode(null);
            const msg = 'Ralat rangkaian semasa menyemak status. Sila cuba lagi.';
            setAssistantError(msg);
            toast.error(msg);
          }
        }
      }, 3000);
    } catch (e) {
      console.error('Regenerate error:', e);
      stopPolling();
      const msg = 'Ralat regenerate. Sila cuba lagi.';
      setAssistantError(msg);
      toast.error(msg);
      setApplying(false);
      setAssistantMode(null);
    }
  }

  function handleBack() {
    if (
      dirty &&
      !window.confirm('Anda ada perubahan tidak disimpan. Tinggal halaman?')
    ) {
      return;
    }
    router.push('/dashboard');
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4"></div>
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

  const applyDisabled =
    applying || (!prompt.trim() && !website?.description);

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-indigo-50/40 to-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-base sm:text-lg font-bold text-gray-900 truncate">
              {website?.business_name || website?.name || 'Editor'}
            </h1>
            {website?.subdomain && (
              <p className="text-xs text-gray-500 truncate">
                {website.subdomain}.binaapp.my
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleBack}
              className="px-3 sm:px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
            >
              ← Kembali
            </button>
            <button
              onClick={saveWebsite}
              disabled={saving}
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Menyimpan…' : 'Simpan'}
              {dirty && !saving && (
                <span
                  className="h-2 w-2 rounded-full bg-amber-300"
                  aria-label="Perubahan belum disimpan"
                />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Body */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-5 pb-24 sm:pb-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* AI Assistant — the hero of the page */}
          <section className="bg-white border border-indigo-100 rounded-2xl p-5 sm:p-6 shadow-sm ring-1 ring-indigo-50">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">🪄</span>
              <h2 className="text-lg font-bold text-gray-900">AI Assistant</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Taip apa-apa perubahan — AI akan tentukan sama ada edit kecil
              atau jana semula keseluruhan laman web.
              {typeof website?.generation_count === 'number' && (
                <span className="ml-1 text-gray-400">
                  (sudah regenerate {Math.max(0, website.generation_count - 1)}x)
                </span>
              )}
            </p>

            {/* Current stored description */}
            {website?.description && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
                <div className="text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">
                  Penerangan semasa
                </div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {website.description}
                </p>
              </div>
            )}

            {/* Style chips */}
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              Pilih gaya (pilihan)
            </label>
            <StyleChipRow
              chips={STYLE_CHIPS}
              selectedChipId={selectedChipId}
              disabled={applying}
              onSelect={(nextId) => {
                const effectivePrev = chipIsStillApplied(prompt, selectedChipId)
                  ? selectedChipId
                  : null;
                const finalNext = nextId === selectedChipId ? null : nextId;
                setPrompt((current) =>
                  applyStyleChip(current, effectivePrev, finalNext)
                );
                setSelectedChipId(finalNext);
              }}
            />

            {/* Single prompt input */}
            <label
              htmlFor="ai-prompt"
              className="block text-xs font-semibold text-gray-700 mb-1.5 mt-4"
            >
              Apa anda nak ubah?
            </label>
            <textarea
              id="ai-prompt"
              value={prompt}
              data-testid="ai-assistant-prompt"
              onChange={(e) => {
                const next = e.target.value;
                setPrompt(next);
                if (selectedChipId && !chipIsStillApplied(next, selectedChipId)) {
                  setSelectedChipId(null);
                }
              }}
              disabled={applying}
              rows={3}
              maxLength={5000}
              placeholder={
                website?.description
                  ? 'Cth: "Tukar warna button jadi merah" atau "Buat lagi modern" (kosongkan untuk jana semula penerangan asal)'
                  : 'Cth: "Tukar warna button jadi merah" atau "Buat lagi modern"'
              }
              className="w-full border border-gray-300 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50 disabled:cursor-not-allowed resize-vertical"
            />

            {/* Quick suggestions */}
            <div className="mt-3 flex flex-wrap gap-2">
              {QUICK_SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled={applying}
                  onClick={() => {
                    setPrompt(s);
                    setSelectedChipId(null);
                  }}
                  className="text-xs bg-gray-100 text-gray-700 px-3 py-1.5 rounded-full hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Detected intent badge */}
            {detected && (
              <div
                className="mt-4 flex items-start gap-2"
                data-testid="detected-intent"
                data-intent={detected.intent}
              >
                <span
                  className={[
                    'shrink-0 inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full',
                    detected.intent === 'quick_edit'
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-indigo-100 text-indigo-700',
                  ].join(' ')}
                  title={
                    detected.indicators.length
                      ? `${detected.reason} (${detected.indicators.join(', ')})`
                      : detected.reason
                  }
                >
                  {detected.intent === 'quick_edit'
                    ? '🔧 Edit pantas'
                    : '🎨 Jana semula penuh'}
                </span>
                <span className="text-xs text-gray-500 leading-relaxed">
                  {detected.reason}
                </span>
              </div>
            )}

            {assistantError && (
              <div className="mt-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                {assistantError}
              </div>
            )}

            {/* Apply button */}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                data-testid="apply-changes"
                onClick={applyChanges}
                disabled={applyDisabled}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {applying ? '⏳ Memproses…' : '🪄 Laksanakan Perubahan'}
              </button>
              {applying && assistantMode === 'full_regenerate' && (
                <span className="text-xs text-gray-500">
                  {pollText || 'Menjana laman web baru...'}
                </span>
              )}
              {applying && assistantMode === 'quick_edit' && (
                <span className="text-xs text-gray-500">
                  AI sedang membuat perubahan…
                </span>
              )}
            </div>
          </section>

          {/* Live preview */}
          <section className="lg:sticky lg:top-20 self-start w-full">
            <div className="flex flex-col border border-gray-200 rounded-2xl overflow-hidden shadow-sm bg-white">
              <div className="bg-gray-100 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-700">
                  👁 Pratonton
                </h2>
                {dirty && (
                  <span className="text-[11px] font-medium text-amber-600">
                    Belum disimpan
                  </span>
                )}
              </div>
              <iframe
                srcDoc={html}
                className="w-full h-[55vh] lg:h-[calc(100vh-9rem)] border-0 bg-white"
                title="Website Preview"
                sandbox="allow-scripts allow-same-origin allow-forms"
              />
            </div>
          </section>
        </div>
      </main>

      {/* Mobile sticky save bar */}
      <div className="sm:hidden fixed bottom-0 inset-x-0 z-30 bg-white border-t border-gray-200 px-4 py-3">
        <button
          onClick={saveWebsite}
          disabled={saving}
          className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-3 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Menyimpan…' : 'Simpan'}
          {dirty && !saving && (
            <span className="h-2 w-2 rounded-full bg-amber-300" />
          )}
        </button>
      </div>

      {/* Full-regenerate confirm modal */}
      {showRegenerateConfirm && (
        <RegenerateConfirmModal
          uploadedImageCount={uploadedImageCount}
          acknowledgeReplace={acknowledgeReplace}
          onAcknowledgeChange={setAcknowledgeReplace}
          onCancel={() => setShowRegenerateConfirm(false)}
          onConfirm={() => {
            setShowRegenerateConfirm(false);
            runRegenerate();
          }}
        />
      )}
    </div>
  );
}

interface StyleChipRowProps {
  chips: readonly {
    id: StyleChipId;
    icon: string;
    label: string;
  }[];
  selectedChipId: StyleChipId | null;
  disabled: boolean;
  onSelect: (chipId: StyleChipId) => void;
}

/**
 * Horizontal row of style hint chips above the prompt box. Single-select
 * (radio behaviour). Tapping the active chip clears it. On mobile the row
 * scrolls horizontally; on desktop it wraps.
 */
function StyleChipRow({
  chips,
  selectedChipId,
  disabled,
  onSelect,
}: StyleChipRowProps) {
  return (
    <div
      role="radiogroup"
      aria-label="Gaya regenerate"
      className="flex flex-nowrap md:flex-wrap items-center gap-2 mb-1 overflow-x-auto md:overflow-visible -mx-1 px-1 pb-1"
    >
      {chips.map((chip) => {
        const active = chip.id === selectedChipId;
        return (
          <button
            key={chip.id}
            type="button"
            role="radio"
            aria-checked={active}
            aria-pressed={active}
            aria-label={chip.label}
            data-testid={`style-chip-${chip.id}`}
            data-active={active ? 'true' : 'false'}
            disabled={disabled}
            onClick={() => onSelect(chip.id)}
            className={[
              'shrink-0 inline-flex items-center gap-1 h-8 px-3 rounded-full',
              'text-xs font-medium whitespace-nowrap transition-colors',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-1',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              active
                ? 'bg-indigo-600 text-white border border-indigo-600 hover:bg-indigo-700'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
            ].join(' ')}
          >
            <span aria-hidden="true">{chip.icon}</span>
            <span>{chip.label}</span>
            {active && (
              <span aria-hidden="true" className="ml-0.5">
                ✓
              </span>
            )}
          </button>
        );
      })}
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
  const disabledReason = confirmDisabled
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
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              aria-describedby="regenerate-ack-help"
            />
            <span id="regenerate-ack-help" className="text-sm text-gray-800">
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
            aria-describedby={
              confirmDisabled ? 'regenerate-confirm-help' : undefined
            }
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
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

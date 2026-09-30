'use client';

/**
 * /admin/tiktok — publish to BinaApp's own TikTok account (@binaapp.my).
 *
 * Admin-only: every backend call goes through `require_admin`; a 403 renders
 * the same "Akses Ditolak" screen as /admin, a 401 sends to login.
 *
 * Flow: Connect TikTok → TikTok authorize page → /api/tiktok/callback →
 * back here with ?tiktok=callback&code&state → POST oauth/callback with the
 * admin's bearer token → account card shows the avatar + display name.
 * Then the composer (TikTokComposer) drives creator_info → post → status.
 */

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui';
import { confirmDialog } from '@/components/ui/popups';
import { TikTokAccountCard } from '@/components/admin/tiktok/TikTokAccountCard';
import { TikTokComposer } from '@/components/admin/tiktok/TikTokComposer';
import { getStoredToken } from '@/lib/supabase';
import {
  completeTikTokOAuth,
  describeStatus,
  disconnectTikTok,
  fetchTikTokAccount,
  fetchTikTokConfig,
  fetchTikTokPost,
  fetchTikTokPosts,
  isPostActive,
  startTikTokOAuth,
  type TikTokAccount,
  type TikTokConfig,
  type TikTokPost,
} from '@/lib/tiktok';

const POLL_MS = 4000;

function AdminTikTokPageInner() {
  const router = useRouter();
  const search = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);
  const [config, setConfig] = useState<TikTokConfig | null>(null);
  const [account, setAccount] = useState<TikTokAccount | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [posts, setPosts] = useState<TikTokPost[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const callbackHandled = useRef(false);

  const handleError = useCallback(
    (err: unknown) => {
      const e = err as { status?: number; message?: string; code?: string | null };
      if (e.status === 401 && e.code === 'not_authenticated') {
        router.push('/login?redirect=/admin/tiktok');
        return true;
      }
      if (e.status === 403) {
        setAccessDenied(true);
        return true;
      }
      return false;
    },
    [router],
  );

  const loadAll = useCallback(async () => {
    try {
      const [cfg, acc, list] = await Promise.all([fetchTikTokConfig(), fetchTikTokAccount(), fetchTikTokPosts(10)]);
      setConfig(cfg);
      setAccount(acc.account);
      setPosts(list.posts);
    } catch (err) {
      if (!handleError(err)) toast.error((err as Error).message || 'Could not load TikTok settings');
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  // Initial load + OAuth return.
  useEffect(() => {
    if (!getStoredToken()) {
      router.push('/login?redirect=/admin/tiktok');
      return;
    }
    const kind = search.get('tiktok');
    if (kind === 'callback' && !callbackHandled.current) {
      callbackHandled.current = true;
      const code = search.get('code') || '';
      const state = search.get('state') || '';
      setConnecting(true);
      completeTikTokOAuth(code, state)
        .then((res) => {
          setAccount(res.account);
          toast.success(`Connected ${res.account.display_name || 'TikTok account'}`);
        })
        .catch((err) => {
          if (!handleError(err)) toast.error((err as Error).message || 'TikTok connection failed');
        })
        .finally(() => {
          setConnecting(false);
          router.replace('/admin/tiktok'); // drop code/state from the URL
          loadAll();
        });
      return;
    }
    if (kind === 'error' && !callbackHandled.current) {
      callbackHandled.current = true;
      const reason = search.get('reason') || 'unknown';
      const description = search.get('description');
      toast.error(`TikTok did not authorise the app: ${reason}${description ? ` — ${description}` : ''}`);
      router.replace('/admin/tiktok');
    }
    loadAll();
  }, [search, router, loadAll, handleError]);

  // Poll any in-flight post until it settles.
  useEffect(() => {
    const active = posts.filter(isPostActive);
    if (!active.length) return;
    const timer = setInterval(async () => {
      for (const p of active) {
        try {
          const { post } = await fetchTikTokPost(p.id);
          setPosts((prev) => prev.map((x) => (x.id === post.id ? post : x)));
          if (!isPostActive(post)) {
            const s = describeStatus(post);
            if (s.tone === 'ok') toast.success(s.label);
            else if (s.tone === 'err') toast.error(s.label);
          }
        } catch (err) {
          if (handleError(err)) return;
        }
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [posts, handleError]);

  const onConnect = async () => {
    setConnecting(true);
    try {
      const { authorize_url } = await startTikTokOAuth();
      window.location.assign(authorize_url);
    } catch (err) {
      setConnecting(false);
      if (!handleError(err)) toast.error((err as Error).message || 'Could not start TikTok login');
    }
  };

  const onDisconnect = async () => {
    const ok = await confirmDialog({
      title: 'Disconnect TikTok?',
      message: 'The access token will be revoked at TikTok and the stored tokens deleted. Posting stops until you connect again.',
      confirmText: 'Disconnect',
      cancelText: 'Keep connected',
      variant: 'danger',
    });
    if (!ok) return;
    try {
      const res = await disconnectTikTok();
      setAccount(null);
      setPosts([]);
      toast.success(res.revoked ? 'TikTok disconnected and token revoked' : 'TikTok disconnected (tokens deleted)');
    } catch (err) {
      if (!handleError(err)) toast.error((err as Error).message || 'Could not disconnect');
    }
  };

  const onRefresh = async () => {
    try {
      const res = await fetchTikTokAccount(true);
      setAccount(res.account);
      toast.success('Profile refreshed from TikTok');
    } catch (err) {
      if (!handleError(err)) toast.error((err as Error).message || 'Could not refresh');
    }
  };

  const onAuthError = useCallback((message: string) => {
    setAccount((a) => (a ? { ...a, status: 'reauth_required', last_error: message } : a));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading…</p>
        </div>
      </div>
    );
  }

  if (accessDenied) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-2xl mb-2">🔒</p>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">Akses Ditolak</h2>
          <p className="text-sm text-gray-500 mb-4">Anda tidak mempunyai akses admin.</p>
          <Link href="/profile" className="text-sm text-blue-600 hover:underline">
            Kembali ke Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const connected = !!account && account.status === 'connected';

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-gray-800">TikTok Publishing</h1>
            <p className="text-xs text-gray-500">Post to BinaApp&apos;s own TikTok account from the admin dashboard</p>
          </div>
          <Link href="/admin" className="text-sm text-blue-600 hover:underline">
            ← Admin Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <TikTokAccountCard
          config={config}
          account={account}
          connecting={connecting}
          onConnect={onConnect}
          onDisconnect={onDisconnect}
          onRefresh={onRefresh}
        />

        {notice && (
          <p className="rounded-xl bg-sky-50 px-4 py-3 text-sm text-sky-800" role="status">
            {notice}
          </p>
        )}

        {connected && config && account && (
          <TikTokComposer
            config={config}
            account={account}
            onAuthError={onAuthError}
            onPostCreated={(post, msg) => {
              setPosts((prev) => [post, ...prev]);
              setNotice(msg);
              toast.success(post.mode === 'inbox' ? 'Sent to TikTok — processing' : 'Sent to TikTok — processing');
            }}
          />
        )}

        <section className="rounded-2xl border border-ink-200 bg-white p-5 shadow-soft" aria-labelledby="tt-posts-h">
          <div className="flex items-center justify-between">
            <h2 id="tt-posts-h" className="text-base font-semibold text-ink-900">
              Recent posts
            </h2>
            <Button variant="ghost" size="sm" onClick={loadAll}>
              Refresh
            </Button>
          </div>
          {posts.length === 0 ? (
            <p className="mt-3 text-sm text-ink-500">Nothing posted from BinaApp yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-ink-100">
              {posts.map((p) => {
                const s = describeStatus(p);
                const tone =
                  s.tone === 'ok' ? 'text-emerald-600' : s.tone === 'err' ? 'text-red-600' : 'text-sky-600';
                return (
                  <li key={p.id} className="py-3 flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink-900 truncate">
                        {p.title || (p.media_type === 'photo' ? 'Photo post' : 'Video')}{' '}
                        <span className="text-xs font-normal text-ink-500">
                          · {p.mode === 'direct' ? 'Post now' : 'Draft'} · {p.media_type}
                          {p.privacy_level ? ` · ${p.privacy_level}` : ''}
                        </span>
                      </p>
                      <p className={`text-sm ${tone}`} aria-live="polite">
                        {isPostActive(p) && (
                          <span className="inline-block w-3 h-3 mr-1 align-middle border-2 border-current border-t-transparent rounded-full animate-spin" />
                        )}
                        {s.label}
                        {p.fail_reason && p.status === 'failed' && (
                          <span className="text-xs text-ink-500"> ({p.fail_reason})</span>
                        )}
                      </p>
                      {p.status === 'published' && p.privacy_level === 'SELF_ONLY' && (
                        <p className="text-xs text-ink-500">
                          Visible only to the account owner. Open the TikTok app → Profile to see it.
                        </p>
                      )}
                    </div>
                    <time className="text-xs text-ink-500" dateTime={p.created_at}>
                      {p.created_at ? new Date(p.created_at).toLocaleString() : ''}
                    </time>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

/**
 * `useSearchParams` must sit under a Suspense boundary for Next 14's static
 * prerender of client pages; the fallback mirrors the loading state.
 */
export default function AdminTikTokPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <AdminTikTokPageInner />
    </Suspense>
  );
}

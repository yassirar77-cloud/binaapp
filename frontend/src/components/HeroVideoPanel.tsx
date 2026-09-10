'use client';

/**
 * Hero Video Background — a short AI-generated clip that loops behind the
 * hero, with a readable scrim over it.
 *
 * Two different buttons live here and the copy keeps them apart on purpose:
 *
 *  - "Jana video" calls the AI (GLM / CogVideoX). It takes a minute or three
 *    and the panel polls until the clip lands — the poll that sees it also
 *    puts it on the page and republishes, so there is no second "apply" step.
 *  - Everything else (overlay, text colour, mobile behaviour, remove) is a
 *    credit-free HTML patch that reuses the clip already on the page.
 *
 * The panel renders nothing at all when the feature is switched off on the
 * server (the options call 404s), so a flag flip needs no frontend deploy.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import {
  HERO_VIDEO_CONNECTION_LOST,
  HERO_VIDEO_MAX_POLL_FAILURES,
  fetchHeroVideoOptions,
  startHeroVideoPurchase,
  isTransientFetchError,
  fetchHeroVideoState,
  heroVideoJobErrorMessage,
  isHeroVideoJobActive,
  pollHeroVideoJob,
  removeHeroVideo,
  startHeroVideo,
  updateHeroVideoLook,
  type HeroVideoJob,
  type HeroVideoLook,
  type HeroVideoOptions,
  type HeroVideoOverlay,
  type HeroVideoSettings,
  type HeroVideoState,
} from '@/lib/heroVideo';
import { getApiAuthToken, getCurrentUser } from '@/lib/supabase';

interface Props {
  websiteId: string;
  /** Called with the patched HTML so the live preview updates immediately. */
  onHtmlChange: (html: string) => void;
}

const OVERLAY_LABELS: Record<HeroVideoOverlay, string> = {
  dark: '🌑 Gelap',
  light: '🌕 Cerah',
  none: '🚫 Tiada',
};

const DEFAULT_LOOK: Required<HeroVideoLook> = {
  overlay: 'dark',
  overlay_opacity: 0.45,
  text_mode: 'auto',
  show_on_mobile: true,
};

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s.toString().padStart(2, '0')}s` : `${s}s`;
}

export default function HeroVideoPanel({ websiteId, onHtmlChange }: Props) {
  // `undefined` = still loading, `null` = feature off → render nothing.
  const [options, setOptions] = useState<HeroVideoOptions | null | undefined>(
    undefined
  );
  const [state, setState] = useState<HeroVideoState | null>(null);
  const [job, setJob] = useState<HeroVideoJob | null>(null);
  const [style, setStyle] = useState('cinematic');
  const [prompt, setPrompt] = useState('');
  const [look, setLook] = useState<Required<HeroVideoLook>>(DEFAULT_LOOK);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tickTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const unmounted = useRef(false);
  // Consecutive dropped polls in the current watch; reset by any success.
  const pollFailures = useRef(0);

  const stopTimers = useCallback(() => {
    if (pollTimer.current) clearTimeout(pollTimer.current);
    if (tickTimer.current) clearInterval(tickTimer.current);
    pollTimer.current = null;
    tickTimer.current = null;
  }, []);

  useEffect(() => {
    unmounted.current = false;
    return () => {
      unmounted.current = true;
      stopTimers();
    };
  }, [stopTimers]);

  const syncLookFrom = useCallback((settings: HeroVideoSettings | null) => {
    if (!settings) return;
    setLook({
      overlay: settings.overlay,
      overlay_opacity: settings.overlay_opacity,
      text_mode: settings.text_mode,
      show_on_mobile: settings.show_on_mobile,
    });
  }, []);

  /**
   * Poll a job until it leaves the processing/storing states. The poll that
   * observes completion carries the patched HTML — push it into the preview.
   */
  const watchJob = useCallback(
    (jobId: string, intervalSeconds: number) => {
      stopTimers();
      setElapsed(0);
      tickTimer.current = setInterval(() => setElapsed((s) => s + 1), 1000);

      const tick = async () => {
        if (unmounted.current) return;
        try {
          const token = await getApiAuthToken();
          const next = await pollHeroVideoJob(websiteId, jobId, token);
          if (unmounted.current) return;
          if (pollFailures.current > 0) {
            pollFailures.current = 0;
            setError((prev) => (prev === HERO_VIDEO_CONNECTION_LOST ? null : prev));
          }
          setJob(next);
          if (isHeroVideoJobActive(next)) {
            pollTimer.current = setTimeout(tick, intervalSeconds * 1000);
            return;
          }
          stopTimers();
          if (next.status === 'completed') {
            if (next.html_content) onHtmlChange(next.html_content);
            if (next.settings) {
              syncLookFrom(next.settings);
              setState((prev) =>
                prev
                  ? { ...prev, has_video: true, settings: next.settings || null, job: null }
                  : prev
              );
            }
            if (next.warning) {
              toast(next.message || 'Video disimpan, laman langsung belum dikemas kini.');
            } else {
              toast.success(next.message || 'Video latar hero telah dipasang.');
            }
          } else {
            const message = heroVideoJobErrorMessage(next.error);
            setError(message);
            toast.error(message);
          }
        } catch (err) {
          if (unmounted.current) return;
          // A dropped request (mobile data blip, tab sent to background) is
          // not a failed job — the clip is still being made on the server.
          // Keep the job, say so in Malay, and poll again a little slower.
          if (isTransientFetchError(err) && ++pollFailures.current < HERO_VIDEO_MAX_POLL_FAILURES) {
            setError(HERO_VIDEO_CONNECTION_LOST);
            pollTimer.current = setTimeout(
              tick,
              Math.min(intervalSeconds * (1 + pollFailures.current), 30) * 1000
            );
            return;
          }
          stopTimers();
          const message = isTransientFetchError(err)
            ? 'Sambungan terputus berulang kali. Muat semula halaman ini untuk menyambung semula penjanaan video.'
            : err instanceof Error
              ? err.message
              : 'Gagal menyemak status video.';
          setError(message);
          setJob(null);
        }
      };

      pollFailures.current = 0;
      pollTimer.current = setTimeout(tick, Math.min(intervalSeconds, 3) * 1000);
    },
    [websiteId, onHtmlChange, stopTimers, syncLookFrom]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const catalogue = await fetchHeroVideoOptions();
        if (cancelled) return;
        setOptions(catalogue);
        if (!catalogue) return;
        const token = await getApiAuthToken();
        const current = await fetchHeroVideoState(websiteId, token);
        if (cancelled) return;
        setState(current);
        syncLookFrom(current.settings);
        // Resume watching a job that was started in another tab / before a
        // reload rather than leaving it orphaned.
        if (current.job && isHeroVideoJobActive(current.job)) {
          setJob(current.job);
          watchJob(current.job.job_id, catalogue.poll_interval_seconds);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            isTransientFetchError(err)
              ? 'Sambungan terputus semasa memuatkan video latar. Muat semula halaman ini.'
              : err instanceof Error
                ? err.message
                : 'Gagal memuatkan video latar.'
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // watchJob/syncLookFrom are stable for a given websiteId.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [websiteId]);

  const generate = async () => {
    if (!options) return;
    setBusy('generate');
    setError(null);
    try {
      const token = await getApiAuthToken();
      const started = await startHeroVideo(
        websiteId,
        { style, prompt: prompt.trim() || undefined, ...look },
        token
      );
      setJob({
        job_id: started.job_id,
        status: started.status,
        error: null,
        video_url: null,
        poster_url: null,
        applied: false,
        live_site_updated: false,
        elapsed_seconds: 0,
      });
      toast(started.message || 'Video sedang dijana…');
      watchJob(started.job_id, started.poll_interval_seconds || options.poll_interval_seconds);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Gagal memulakan penjanaan video.';
      setError(message);
      toast.error(message);
    } finally {
      setBusy(null);
    }
  };

  const applyLook = async (patch: HeroVideoLook, busyKey: string) => {
    const nextLook = { ...look, ...patch };
    setLook(nextLook);
    if (!state?.has_video) return; // Only a preference until a clip exists.
    setBusy(busyKey);
    setError(null);
    try {
      const token = await getApiAuthToken();
      const result = await updateHeroVideoLook(websiteId, patch, token);
      if (!result.changed) return;
      if (result.html_content) onHtmlChange(result.html_content);
      if (result.settings) {
        setState((prev) => (prev ? { ...prev, settings: result.settings || null } : prev));
      }
      toast.success(result.message || 'Tetapan video dikemas kini.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Gagal mengemas kini tetapan.';
      setError(message);
      toast.error(message);
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!window.confirm('Buang video latar dari bahagian hero?')) return;
    setBusy('remove');
    setError(null);
    try {
      const token = await getApiAuthToken();
      const result = await removeHeroVideo(websiteId, token);
      if (result.html_content) onHtmlChange(result.html_content);
      setState((prev) => (prev ? { ...prev, has_video: false, settings: null } : prev));
      setJob(null);
      toast.success(result.message || 'Video latar hero telah dibuang.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Gagal membuang video.';
      setError(message);
      toast.error(message);
    } finally {
      setBusy(null);
    }
  };

  if (options === null) return null; // Feature off server-side.

  const jobActive = isHeroVideoJobActive(job);
  const hasVideo = !!state?.has_video;
  const allowed = state?.allowed ?? true;
  const heroFound = state?.hero_found ?? true;
  const freeAccess = state?.free_access ?? true;
  const credits = state?.credits ?? 0;
  const requiresUpgrade = !!state?.requires_upgrade;
  const priceRm = state?.price_rm ?? options?.price_rm ?? 5;
  const disableAll = busy !== null || jobActive;

  const buyCredit = async () => {
    setBusy('buy');
    setError(null);
    try {
      const [user, token] = await Promise.all([getCurrentUser(), getApiAuthToken()]);
      if (!user?.id) {
        throw new Error('Sila log masuk semula untuk meneruskan pembayaran.');
      }
      await startHeroVideoPurchase({
        userId: user.id,
        token,
        returnTo: window.location.pathname,
      });
      // The browser is now on its way to ToyyibPay.
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Gagal memulakan pembayaran.';
      setError(message);
      toast.error(message);
      setBusy(null);
    }
  };

  return (
    <section
      className="bg-white border border-gray-200 rounded-2xl p-5 sm:p-6 shadow-sm"
      data-testid="hero-video-panel"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-2xl">🎬</span>
        <h2 className="text-lg font-bold text-gray-900">Video Latar Hero</h2>
        <span className="ml-auto text-[11px] font-semibold uppercase tracking-wide text-violet-700 bg-violet-50 border border-violet-200 rounded-full px-2 py-0.5">
          AI Video
        </span>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Klip pendek dijana AI yang bergerak di belakang tajuk utama laman web
        anda. Teks, harga dan gambar anda kekal — hanya latar yang bergerak.
      </p>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {!options ? (
        <div className="h-24 rounded-xl bg-gray-100 animate-pulse" aria-hidden="true" />
      ) : (
        <>
          {/* Current clip */}
          {hasVideo && state?.settings && (
            <div
              className="mb-4 flex items-center gap-3 rounded-xl border border-gray-200 bg-gray-50 p-3"
              data-testid="hero-video-current"
            >
              <video
                className="h-16 w-28 rounded-lg object-cover bg-black"
                src={state.settings.video_url}
                poster={state.settings.poster_url || undefined}
                muted
                loop
                playsInline
                autoPlay
                aria-label="Pratonton video latar semasa"
              />
              <div className="min-w-0 flex-1">
                {/* "telah", not "sedang": this card renders once the clip IS on
                    the page. "sedang dipasang" read as "still being installed"
                    and sent a merchant looking for a problem that wasn't there. */}
                <div className="text-sm font-semibold text-gray-900">Video telah dipasang</div>
                <div className="text-xs text-gray-500">
                  Jana semula untuk klip baharu, atau laraskan lapisan di bawah.
                </div>
              </div>
              <button
                type="button"
                data-testid="remove-hero-video"
                onClick={remove}
                disabled={disableAll}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-red-200 text-red-700 bg-white hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {busy === 'remove' ? '⏳' : '🗑 Buang'}
              </button>
            </div>
          )}

          {/* In-flight job */}
          {jobActive && job && (
            <div
              className="mb-4 rounded-xl border border-violet-200 bg-violet-50 p-3 text-sm text-violet-900"
              role="status"
              data-testid="hero-video-progress"
            >
              <div className="flex items-center gap-2 font-semibold">
                <span className="inline-block h-2 w-2 rounded-full bg-violet-500 animate-pulse" />
                {job.status === 'storing'
                  ? 'Menyimpan video dan memasang pada laman…'
                  : 'AI sedang menjana video…'}
                <span className="ml-auto font-normal text-violet-700 tabular-nums">
                  {formatElapsed(Math.max(elapsed, job.elapsed_seconds || 0))}
                </span>
              </div>
              <div className="mt-1 text-xs text-violet-700">
                Biasanya 1–3 minit. Anda boleh terus mengedit; video akan dipasang
                secara automatik apabila siap.
              </div>
            </div>
          )}

          {!freeAccess && (
            <div
              data-testid="hero-video-credits"
              className={`mb-4 border text-sm rounded-lg p-3 flex flex-wrap items-center justify-between gap-3 ${
                allowed ? 'bg-violet-50 border-violet-200 text-violet-900' : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}
            >
              <div>
                <div className="font-semibold">
                  {allowed
                    ? `Baki kredit video: ${credits}`
                    : `Video latar hero berharga RM${priceRm.toFixed(0)} setiap klip.`}
                </div>
                <div className="text-xs opacity-80 mt-0.5">
                  {allowed
                    ? `Setiap penjanaan menggunakan 1 kredit (RM${priceRm.toFixed(0)}). Kredit dipulangkan jika video gagal dijana.`
                    : requiresUpgrade
                      ? 'Pelan Percuma hanya untuk pratonton. Naik taraf ke Starter (RM5/bulan) untuk terbit laman web dan beli kredit video.'
                      : 'Anda belum ada kredit. Beli 1 kredit untuk menjana video latar.'}
                </div>
              </div>
              {requiresUpgrade && !allowed ? (
                <a
                  href="/dashboard/billing"
                  data-testid="upgrade-for-hero-video"
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-gray-900 text-white hover:bg-black transition-colors"
                >
                  Naik taraf ke Starter — RM5/bulan
                </a>
              ) : (
                <button
                  type="button"
                  data-testid="buy-hero-video-credit"
                  onClick={buyCredit}
                  disabled={disableAll}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-gray-900 text-white hover:bg-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {busy === 'buy' ? '⏳ Menghubungi ToyyibPay…' : `Beli 1 kredit — RM${priceRm.toFixed(0)}`}
                </button>
              )}
            </div>
          )}
          {!heroFound && (
            <div className="mb-4 bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg p-3">
              Bahagian hero tidak dijumpai pada laman web ini, jadi video tidak
              boleh dipasang.
            </div>
          )}

          {/* Style presets */}
          <div className="mb-3">
            <div className="text-sm font-semibold text-gray-700 mb-2">Gaya video</div>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Gaya video">
              {options.styles.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  data-testid={`video-style-${preset.key}`}
                  aria-pressed={style === preset.key}
                  disabled={disableAll}
                  onClick={() => setStyle(preset.key)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors disabled:opacity-50 ${
                    style === preset.key
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {preset.label_ms}
                </button>
              ))}
            </div>
          </div>

          {/* Optional description */}
          <div className="mb-4">
            <label
              htmlFor={`hero-video-prompt-${websiteId}`}
              className="text-sm font-semibold text-gray-700 block mb-1"
            >
              Penerangan (pilihan)
            </label>
            <textarea
              id={`hero-video-prompt-${websiteId}`}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value.slice(0, 400))}
              disabled={disableAll}
              rows={2}
              placeholder="cth: asap naik dari kuali nasi goreng, lampu warung waktu senja"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-200 disabled:bg-gray-50"
            />
            <div className="text-[11px] text-gray-400 text-right">{prompt.length}/400</div>
          </div>

          <button
            type="button"
            data-testid="generate-hero-video"
            onClick={generate}
            disabled={disableAll || !allowed || !heroFound}
            className="w-full sm:w-auto px-5 py-2.5 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy === 'generate'
              ? '⏳ Memulakan…'
              : jobActive
                ? '🎬 Sedang dijana…'
                : hasVideo
                  ? `🎬 Jana video baharu${freeAccess ? '' : ' (1 kredit)'}`
                  : `🎬 Jana video latar${freeAccess ? '' : ' (1 kredit)'}`}
          </button>
          <p className="mt-2 text-[11px] text-gray-400">
            Klip {options.duration_seconds} saat, tanpa bunyi, diulang tanpa henti.
            Menjana video menggunakan AI; melaraskan atau membuangnya adalah percuma.
          </p>

          {/* Look controls — free once a clip exists */}
          <div className="mt-5 pt-5 border-t border-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-sm font-semibold text-gray-700">Lapisan &amp; teks</h3>
              <span className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
                Percuma
              </span>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Lapisan gelap atau cerah di atas video supaya tajuk anda kekal jelas
              dibaca.{!hasVideo ? ' Tetapan ini digunakan apabila video siap.' : ''}
            </p>

            <div className="flex flex-wrap items-center gap-2 mb-3" role="group" aria-label="Lapisan">
              {(Object.keys(OVERLAY_LABELS) as HeroVideoOverlay[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  data-testid={`overlay-${mode}`}
                  aria-pressed={look.overlay === mode}
                  disabled={disableAll}
                  onClick={() => applyLook({ overlay: mode }, `overlay-${mode}`)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors disabled:opacity-50 ${
                    look.overlay === mode
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {busy === `overlay-${mode}` ? '⏳' : OVERLAY_LABELS[mode]}
                </button>
              ))}
            </div>

            <label className="flex items-center gap-3 text-xs text-gray-600 mb-3">
              <span className="w-24 shrink-0">Ketebalan</span>
              <input
                type="range"
                min={0}
                max={0.9}
                step={0.05}
                value={look.overlay_opacity}
                disabled={disableAll || look.overlay === 'none'}
                onChange={(e) => setLook((l) => ({ ...l, overlay_opacity: Number(e.target.value) }))}
                onMouseUp={(e) =>
                  applyLook({ overlay_opacity: Number((e.target as HTMLInputElement).value) }, 'opacity')
                }
                onTouchEnd={(e) =>
                  applyLook({ overlay_opacity: Number((e.target as HTMLInputElement).value) }, 'opacity')
                }
                onKeyUp={(e) =>
                  applyLook({ overlay_opacity: Number((e.target as HTMLInputElement).value) }, 'opacity')
                }
                aria-label="Ketebalan lapisan"
                className="flex-1 accent-violet-600"
              />
              <span className="w-10 text-right tabular-nums">
                {Math.round(look.overlay_opacity * 100)}%
              </span>
            </label>

            <label className="flex items-center gap-2 text-xs text-gray-600">
              <input
                type="checkbox"
                data-testid="show-on-mobile"
                checked={look.show_on_mobile}
                disabled={disableAll}
                onChange={(e) => applyLook({ show_on_mobile: e.target.checked }, 'mobile')}
                className="accent-violet-600"
              />
              Mainkan video pada telefon (nyahtanda untuk paparkan gambar pegun sahaja
              &amp; jimat data)
            </label>
          </div>
        </>
      )}
    </section>
  );
}

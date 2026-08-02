'use client';

/**
 * Design Studio — pick a palette, swap the typography, print a QR poster.
 *
 * Everything in this panel is CREDIT-FREE and instant: it rewrites the colour
 * and font tokens in the page that already exists rather than regenerating it.
 * That distinction is the whole point, so the panel states it plainly — a
 * merchant who has been burned by "tukar warna" costing a generation and
 * returning a different menu needs to know this button is not that button.
 */

import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
  applyTheme,
  fetchCurrentTheme,
  fetchDesignOptions,
  fetchPosterHtml,
  isActivePalette,
  readableTextOn,
  type CurrentTheme,
  type DesignOptions,
  type PaletteOption,
  type ThemePatchRequest,
} from '@/lib/designStudio';
import { getApiAuthToken } from '@/lib/supabase';

interface Props {
  websiteId: string;
  /** True once the site has a subdomain — gates the QR poster. */
  isPublished: boolean;
  /** Called with the repainted HTML so the live preview updates immediately. */
  onHtmlChange: (html: string) => void;
}

export default function DesignStudioPanel({
  websiteId,
  isPublished,
  onHtmlChange,
}: Props) {
  const [options, setOptions] = useState<DesignOptions | null>(null);
  const [current, setCurrent] = useState<CurrentTheme | null>(null);
  const [colorMode, setColorMode] = useState<'light' | 'dark'>('light');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFonts, setShowFonts] = useState(false);
  const [tableNumber, setTableNumber] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [catalogue, token] = await Promise.all([
          fetchDesignOptions(colorMode),
          getApiAuthToken(),
        ]);
        if (cancelled) return;
        setOptions(catalogue);
        const theme = await fetchCurrentTheme(websiteId, token);
        if (!cancelled) setCurrent(theme);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Gagal memuatkan tema.');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [websiteId, colorMode]);

  const patch = useCallback(
    async (body: ThemePatchRequest, busyKey: string) => {
      setBusy(busyKey);
      setError(null);
      try {
        const token = await getApiAuthToken();
        const result = await applyTheme(
          websiteId,
          { color_mode: colorMode, ...body },
          token
        );
        if (!result.changed) {
          toast(result.message || 'Tiada perubahan.');
          return;
        }
        if (result.html_content) onHtmlChange(result.html_content);
        setCurrent((prev) => ({
          source: prev?.source || 'db',
          text_contrast: prev?.text_contrast ?? null,
          palette: { ...(prev?.palette || {}), ...result.palette },
          palette_key: result.palette_key,
          fonts: result.fonts?.heading ? result.fonts : prev?.fonts || {},
        }));
        toast.success(result.message || 'Tema dikemas kini.');
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Gagal menukar tema.';
        setError(message);
        toast.error(message);
      } finally {
        setBusy(null);
      }
    },
    [websiteId, colorMode, onHtmlChange]
  );

  /**
   * The poster endpoint is owner-only, so it cannot be reached by navigating
   * a new tab at it — a top-level navigation sends no Authorization header
   * and the response is a 401. Fetch it with the token instead and write the
   * markup into a tab we opened ourselves.
   *
   * The tab is opened SYNCHRONOUSLY, before the first await: a popup created
   * after an async hop has lost the click's user-gesture and is blocked by
   * default in every current browser.
   */
  const openPoster = async () => {
    const tab = window.open('', '_blank');
    if (!tab) {
      toast.error('Sila benarkan pop-up untuk membuka poster.');
      return;
    }
    setBusy('poster');
    setError(null);
    try {
      const token = await getApiAuthToken();
      const html = await fetchPosterHtml(
        websiteId,
        { table: tableNumber.trim() || undefined },
        token
      );
      tab.document.open();
      tab.document.write(html);
      tab.document.close();
    } catch (err) {
      // Never leave a blank tab sitting there as if it were loading.
      tab.close();
      const message =
        err instanceof Error ? err.message : 'Gagal menjana poster QR.';
      setError(message);
      toast.error(message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="bg-white border border-gray-200 rounded-2xl p-5 sm:p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-2xl">🎨</span>
        <h2 className="text-lg font-bold text-gray-900">Studio Reka Bentuk</h2>
        <span className="ml-auto text-[11px] font-semibold uppercase tracking-wide text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
          Percuma
        </span>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Tukar warna dan font serta-merta. Tiada AI, tiada kredit digunakan —
        teks, harga dan gambar anda kekal sama.
      </p>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {/* Light / dark */}
      <div className="flex items-center gap-2 mb-4">
        {(['light', 'dark'] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            onClick={() => setColorMode(mode)}
            aria-pressed={colorMode === mode}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
              colorMode === mode
                ? 'bg-gray-900 text-white border-gray-900'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {mode === 'light' ? '🌞 Terang' : '🌙 Gelap'}
          </button>
        ))}
        <button
          type="button"
          data-testid="shuffle-design"
          onClick={() => patch({ shuffle: true }, 'shuffle')}
          disabled={busy !== null}
          className="ml-auto px-3 py-1.5 rounded-full text-xs font-semibold border border-indigo-300 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50 transition-colors"
        >
          {busy === 'shuffle' ? '⏳ Menukar…' : '🎲 Cuba warna lain'}
        </button>
      </div>

      {/* Palette swatches */}
      {!options ? (
        <div className="grid grid-cols-4 sm:grid-cols-6 gap-2" aria-hidden="true">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="h-14 rounded-xl bg-gray-100 animate-pulse" />
          ))}
        </div>
      ) : (
        <div
          className="grid grid-cols-4 sm:grid-cols-6 gap-2"
          role="group"
          aria-label="Palet warna"
        >
          {options.palettes.map((palette: PaletteOption) => {
            const active = isActivePalette(palette, current);
            return (
              <button
                key={palette.key}
                type="button"
                data-testid={`palette-${palette.key}`}
                title={palette.label_ms}
                aria-pressed={active}
                disabled={busy !== null}
                onClick={() => patch({ palette: palette.key }, palette.key)}
                className={`relative h-14 rounded-xl overflow-hidden border-2 transition-transform disabled:opacity-60 ${
                  active
                    ? 'border-gray-900 scale-[1.03]'
                    : 'border-transparent hover:scale-[1.03]'
                }`}
                style={{ background: palette.colors.primary }}
              >
                <span
                  className="absolute inset-x-0 bottom-0 h-5 flex items-center justify-center text-[10px] font-semibold"
                  style={{
                    background: palette.colors.surface,
                    color: readableTextOn(palette.colors.surface),
                  }}
                >
                  {palette.label_ms}
                </span>
                {busy === palette.key && (
                  <span className="absolute inset-0 grid place-items-center bg-black/30 text-white text-xs">
                    ⏳
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Typography */}
      <div className="mt-5">
        <button
          type="button"
          onClick={() => setShowFonts((v) => !v)}
          className="text-sm font-semibold text-gray-700 hover:text-gray-900 flex items-center gap-1.5"
          aria-expanded={showFonts}
        >
          <span>🔤 Font</span>
          {current?.fonts?.heading && (
            <span className="font-normal text-gray-500">
              — {current.fonts.heading} / {current.fonts.body}
            </span>
          )}
          <span className="text-gray-400">{showFonts ? '▲' : '▼'}</span>
        </button>

        {showFonts && options && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
            {options.fonts.map((font) => (
              <button
                key={font.key}
                type="button"
                data-testid={`font-${font.key}`}
                disabled={busy !== null}
                onClick={() => patch({ font_key: font.key }, font.key)}
                className="text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/50 disabled:opacity-60 transition-colors"
              >
                <div className="text-sm font-semibold text-gray-900">
                  {font.heading}
                </div>
                <div className="text-xs text-gray-500">
                  + {font.body}
                  {font.vibe ? ` · ${font.vibe}` : ''}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* QR poster */}
      <div className="mt-5 pt-5 border-t border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700 mb-1">
          🖨️ Poster QR
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          Poster A4 sedia cetak dengan kod QR laman web anda — untuk kaunter,
          meja atau risalah.
        </p>
        {isPublished ? (
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={tableNumber}
              onChange={(e) => setTableNumber(e.target.value.slice(0, 8))}
              placeholder="No. meja (pilihan)"
              aria-label="Nombor meja"
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-40 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            />
            <button
              type="button"
              data-testid="open-qr-poster"
              onClick={openPoster}
              disabled={busy === 'poster'}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {busy === 'poster' ? 'Menjana…' : 'Buka poster'}
            </button>
          </div>
        ) : (
          <p className="text-xs text-gray-400">
            Terbitkan laman web anda dahulu untuk menjana kod QR.
          </p>
        )}
      </div>
    </section>
  );
}

'use client';

/**
 * Promo Kit — everything a merchant prints, posts or shares to pull people
 * onto their site, generated free from the site they already have.
 *
 *   📲 Kad kongsi   — the WhatsApp link-preview image (og:image). Automatic
 *                     once published; the button here is a preview/download.
 *   🖼️ Poster story — 1080x1920 PNG with the site QR, for WhatsApp Status
 *                     and Instagram Story.
 *   📇 Simpan nombor — A4 poster whose QR saves the shop's contact (name,
 *                     WhatsApp number, website) straight into a phone.
 *   📶 Wi-Fi        — A4 "scan to join" poster. The SSID and password go to
 *                     the server only to be drawn — they are never stored.
 *
 * Same contract as the Design Studio: no AI, no credit, instant.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import {
  downloadObjectUrl,
  fetchKitHtml,
  fetchKitImageUrl,
} from '@/lib/promoKit';
import { getApiAuthToken } from '@/lib/supabase';

interface Props {
  websiteId: string;
  /** True once the site has a subdomain — everything here needs a live URL. */
  isPublished: boolean;
  subdomain?: string | null;
}

export default function PromoKitPanel({ websiteId, isPublished, subdomain }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ssid, setSsid] = useState('');
  const [wifiPassword, setWifiPassword] = useState('');
  const [reviewUrl, setReviewUrl] = useState('');
  const [waTable, setWaTable] = useState('');

  const fail = (err: unknown, fallback: string) => {
    const message = err instanceof Error ? err.message : fallback;
    setError(message);
    toast.error(message);
  };

  const downloadImage = async (
    key: string,
    path: 'share-card.png' | 'story.png',
    filename: string
  ) => {
    setBusy(key);
    setError(null);
    try {
      const token = await getApiAuthToken();
      const objectUrl = await fetchKitImageUrl(websiteId, path, {}, token);
      downloadObjectUrl(objectUrl, filename);
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      fail(err, 'Gagal menjana imej.');
    } finally {
      setBusy(null);
    }
  };

  /**
   * Posters are owner-only HTML, so the tab is opened synchronously (keeping
   * the click's user-gesture) and the markup fetched with the bearer token —
   * same pattern, for the same 401 reason, as the Design Studio's QR poster.
   */
  const openPoster = async (
    key: string,
    path:
      | 'vcard-poster.html'
      | 'wifi-poster.html'
      | 'menu-poster.html'
      | 'review-poster.html'
      | 'whatsapp-poster.html',
    params: Record<string, string | undefined>
  ) => {
    const tab = window.open('', '_blank');
    if (!tab) {
      toast.error('Sila benarkan pop-up untuk membuka poster.');
      return;
    }
    setBusy(key);
    setError(null);
    try {
      const token = await getApiAuthToken();
      const html = await fetchKitHtml(websiteId, path, params, token);
      tab.document.open();
      tab.document.write(html);
      tab.document.close();
    } catch (err) {
      tab.close();
      fail(err, 'Gagal menjana poster.');
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="bg-white border border-gray-200 rounded-2xl p-5 sm:p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-2xl">📣</span>
        <h2 className="text-lg font-bold text-gray-900">Kit Promosi</h2>
        <span className="ml-auto text-[11px] font-semibold uppercase tracking-wide text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
          Percuma
        </span>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Imej kongsi, poster story, QR simpan-nombor dan QR Wi-Fi — semua dijana
        serta-merta daripada laman web anda, dalam warna jenama anda sendiri.
      </p>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      {!isPublished ? (
        <p className="text-xs text-gray-400">
          Terbitkan laman web anda dahulu untuk menggunakan Kit Promosi.
        </p>
      ) : (
        <div className="space-y-5">
          {/* Share card */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              📲 Kad Kongsi WhatsApp
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              Bila anda kongsi pautan{subdomain ? ` ${subdomain}.binaapp.my` : ''} di
              WhatsApp atau Facebook, ia terbuka sebagai kad berjenama — sudah
              aktif secara automatik. Muat turun salinan untuk semakan:
            </p>
            <button
              type="button"
              data-testid="download-share-card"
              onClick={() =>
                downloadImage('share', 'share-card.png', `${subdomain || 'laman'}-kad-kongsi.png`)
              }
              disabled={busy === 'share'}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {busy === 'share' ? 'Menjana…' : 'Muat turun kad'}
            </button>
          </div>

          {/* Story poster */}
          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              🖼️ Poster Story / Status
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              Imej menegak (1080×1920) dengan kod QR laman anda — sedia untuk
              WhatsApp Status atau Instagram Story.
            </p>
            <button
              type="button"
              data-testid="download-story"
              onClick={() =>
                downloadImage('story', 'story.png', `${subdomain || 'laman'}-story.png`)
              }
              disabled={busy === 'story'}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {busy === 'story' ? 'Menjana…' : 'Muat turun poster'}
            </button>
          </div>

          {/* Menu poster */}
          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              📄 Menu / Senarai Harga A4
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              Menu sedia cetak dalam warna laman anda — item dan harga diambil
              terus daripada menu anda. Tukar harga, cetak semula, siap.
            </p>
            <button
              type="button"
              data-testid="open-menu-poster"
              onClick={() => openPoster('menu', 'menu-poster.html', {})}
              disabled={busy === 'menu'}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {busy === 'menu' ? 'Menjana…' : 'Buka menu A4'}
            </button>
          </div>

          {/* WhatsApp order poster */}
          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              💬 QR Pesan WhatsApp
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              Pelanggan imbas — WhatsApp terbuka dengan mesej pesanan siap
              ditaip. Letak nombor meja untuk tahu pesanan datang dari meja
              mana.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={waTable}
                onChange={(e) => setWaTable(e.target.value.slice(0, 8))}
                placeholder="No. meja (pilihan)"
                aria-label="Nombor meja"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-40 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              <button
                type="button"
                data-testid="open-whatsapp-poster"
                onClick={() =>
                  openPoster('whatsapp', 'whatsapp-poster.html', {
                    table: waTable.trim() || undefined,
                  })
                }
                disabled={busy === 'whatsapp'}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
              >
                {busy === 'whatsapp' ? 'Menjana…' : 'Buka poster A4'}
              </button>
            </div>
          </div>

          {/* Google review poster */}
          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              ⭐ QR Ulasan Google
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              Poster “beri kami 5 bintang” — QR terus ke halaman ulasan Google
              anda. Tampal pautan ulasan Google anda (google.com, g.page atau
              maps.app.goo.gl).
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="url"
                value={reviewUrl}
                onChange={(e) => setReviewUrl(e.target.value.slice(0, 500))}
                placeholder="https://g.page/r/..."
                aria-label="Pautan ulasan Google"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-64 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              <button
                type="button"
                data-testid="open-review-poster"
                onClick={() =>
                  openPoster('review', 'review-poster.html', {
                    review_url: reviewUrl.trim(),
                  })
                }
                disabled={busy === 'review' || !reviewUrl.trim()}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
              >
                {busy === 'review' ? 'Menjana…' : 'Buka poster A4'}
              </button>
            </div>
          </div>

          {/* vCard poster */}
          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              📇 QR Simpan Nombor
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              Pelanggan imbas sekali — nama kedai, nombor WhatsApp dan laman web
              anda terus tersimpan dalam telefon mereka. Nombor diambil daripada
              laman web anda sendiri.
            </p>
            <button
              type="button"
              data-testid="open-vcard-poster"
              onClick={() => openPoster('vcard', 'vcard-poster.html', {})}
              disabled={busy === 'vcard'}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
            >
              {busy === 'vcard' ? 'Menjana…' : 'Buka poster A4'}
            </button>
          </div>

          {/* Wi-Fi poster */}
          <div className="pt-4 border-t border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              📶 QR Wi-Fi Kedai
            </h3>
            <p className="text-xs text-gray-500 mb-2">
              Poster “imbas untuk sambung” — pelanggan tak perlu taip kata
              laluan. Maklumat Wi-Fi anda tidak disimpan di mana-mana.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={ssid}
                onChange={(e) => setSsid(e.target.value.slice(0, 32))}
                placeholder="Nama Wi-Fi (SSID)"
                aria-label="Nama Wi-Fi"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-44 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              <input
                type="text"
                value={wifiPassword}
                onChange={(e) => setWifiPassword(e.target.value.slice(0, 63))}
                placeholder="Kata laluan"
                aria-label="Kata laluan Wi-Fi"
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm w-40 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              <button
                type="button"
                data-testid="open-wifi-poster"
                onClick={() =>
                  openPoster('wifi', 'wifi-poster.html', {
                    ssid: ssid.trim(),
                    password: wifiPassword,
                  })
                }
                disabled={busy === 'wifi' || !ssid.trim()}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-50 transition-colors"
              >
                {busy === 'wifi' ? 'Menjana…' : 'Buka poster A4'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

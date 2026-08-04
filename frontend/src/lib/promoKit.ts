/**
 * Promo Kit client — share images, vCard QR and Wi-Fi QR posters.
 *
 * The matching backend lives in `api/v1/endpoints/promo_kit.py`. Everything
 * is rendered offline from the merchant's own site data (name, palette,
 * published URL, the phone number on their page) — no AI call and no credit,
 * same contract as the Design Studio and the QR poster.
 *
 * All endpoints are owner-only, so nothing here can be reached by pointing a
 * new tab at the URL — a top-level navigation carries no Authorization
 * header. HTML posters are fetched with the token and written into a tab the
 * caller opened; images are fetched as blobs and downloaded/previewed via an
 * object URL. Tokens never go into URLs.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

export type KitLanguage = 'ms' | 'en';

/** Malay error copy for the promo-kit endpoints' failure shapes. */
export function kitErrorMessage(status: number, detail?: unknown): string {
  if (status === 401 || status === 403) {
    return 'Sesi tamat. Sila log masuk semula.';
  }
  if (status === 404) {
    return 'Laman web tidak dijumpai.';
  }
  const code =
    detail && typeof detail === 'object' && 'error' in (detail as object)
      ? String((detail as { error: unknown }).error)
      : '';
  if (code === 'not_published') {
    return 'Terbitkan laman web anda dahulu.';
  }
  if (code === 'no_phone_found') {
    return 'Tiada nombor telefon di laman web anda. Tambah pautan WhatsApp dahulu.';
  }
  if (status === 503) {
    return 'Penjana imej tidak tersedia buat masa ini. Cuba lagi nanti.';
  }
  return 'Gagal menjana. Cuba lagi.';
}

function kitUrl(
  websiteId: string,
  path: string,
  params: Record<string, string | undefined> = {}
): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) query.set(key, value);
  }
  const qs = query.toString();
  return `${API_BASE}/api/v1/websites/${websiteId}/${path}${qs ? `?${qs}` : ''}`;
}

async function kitFetch(
  websiteId: string,
  path: string,
  params: Record<string, string | undefined>,
  token: string | null
): Promise<Response> {
  const resp = await fetch(kitUrl(websiteId, path, params), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(kitErrorMessage(resp.status, body?.detail));
  }
  return resp;
}

/** Printable poster HTML (vcard-poster.html / wifi-poster.html). */
export async function fetchKitHtml(
  websiteId: string,
  path: 'vcard-poster.html' | 'wifi-poster.html',
  params: Record<string, string | undefined>,
  token: string | null
): Promise<string> {
  const resp = await kitFetch(websiteId, path, params, token);
  return resp.text();
}

/**
 * A PNG (share-card.png / story.png) as an object URL for preview/download.
 * Callers must `URL.revokeObjectURL` when done with it.
 */
export async function fetchKitImageUrl(
  websiteId: string,
  path: 'share-card.png' | 'story.png',
  params: Record<string, string | undefined>,
  token: string | null
): Promise<string> {
  const resp = await kitFetch(websiteId, path, params, token);
  return URL.createObjectURL(await resp.blob());
}

/** Trigger a browser download of an object URL. */
export function downloadObjectUrl(objectUrl: string, filename: string): void {
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

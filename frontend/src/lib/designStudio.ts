/**
 * Design Studio client — credit-free colour & typography control.
 *
 * The matching backend lives in `api/v1/endpoints/design_studio.py`. Nothing
 * here consumes a generation credit: a repaint rewrites the colour tokens in
 * the page that already exists, so the merchant's copy, prices and photos
 * cannot move. That guarantee is the reason this path exists separately from
 * the AI assistant, and the UI must say so.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

export interface PaletteColors {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  surface: string;
  text: string;
  text_muted?: string;
  border?: string;
}

export interface PaletteOption {
  key: string;
  label_ms: string;
  label_en: string;
  colors: PaletteColors;
}

export interface FontOption {
  key: string;
  heading: string;
  body: string;
  vibe: string;
  business_type: string;
}

export interface StyleOption {
  key: string;
  label_ms: string;
  label_en: string;
  personality: string;
  description: string;
}

export interface DesignOptions {
  palettes: PaletteOption[];
  fonts: FontOption[];
  styles: StyleOption[];
}

export interface CurrentTheme {
  palette: Partial<PaletteColors>;
  palette_key: string | null;
  fonts: { heading?: string; body?: string };
  text_contrast: number | null;
  source: string;
}

export interface ThemePatchRequest {
  palette?: string;
  colors?: Partial<PaletteColors>;
  color_mode?: 'light' | 'dark';
  font_key?: string;
  shuffle?: boolean;
  shuffle_step?: number;
}

export interface ThemePatchResult {
  success: boolean;
  changed: boolean;
  message: string;
  palette_key: string | null;
  palette: Partial<PaletteColors>;
  fonts: { heading?: string; body?: string };
  live_site_updated: boolean;
  html_content?: string;
  notes?: string[];
  warning?: string;
}

/** Malay error copy for the failure shapes the endpoint can return. */
export function themeErrorMessage(status: number, detail?: unknown): string {
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
  if (code === 'no_balanced_html_base') {
    return 'Laman web ini perlu dijana semula sebelum warnanya boleh ditukar.';
  }
  if (code === 'rewrite_produced_unbalanced_html') {
    return 'Perubahan dibatalkan untuk melindungi laman web anda. Cuba lagi.';
  }
  if (typeof detail === 'string' && detail) return detail;
  return 'Gagal menukar tema. Cuba lagi.';
}

async function authedFetch(
  path: string,
  token: string | null,
  init?: RequestInit
): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
}

/** The palette / font / style catalogue. Public — no token needed. */
export async function fetchDesignOptions(
  colorMode: 'light' | 'dark' = 'light'
): Promise<DesignOptions> {
  const resp = await fetch(
    `${API_BASE}/api/v1/websites/design/options?color_mode=${colorMode}`
  );
  if (!resp.ok) throw new Error(themeErrorMessage(resp.status));
  const data = await resp.json();
  return {
    palettes: data.palettes || [],
    fonts: data.fonts || [],
    styles: data.styles || [],
  };
}

/** What the live page is wearing right now. */
export async function fetchCurrentTheme(
  websiteId: string,
  token: string | null
): Promise<CurrentTheme> {
  const resp = await authedFetch(`/api/v1/websites/${websiteId}/theme`, token);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(themeErrorMessage(resp.status, body?.detail));
  }
  return resp.json();
}

/** Repaint. Credit-free — never triggers a regeneration. */
export async function applyTheme(
  websiteId: string,
  body: ThemePatchRequest,
  token: string | null
): Promise<ThemePatchResult> {
  const resp = await authedFetch(`/api/v1/websites/${websiteId}/theme`, token, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(themeErrorMessage(resp.status, data?.detail));
  }
  return data as ThemePatchResult;
}

/** Malay error copy for the QR endpoints' failure shapes. */
export function qrErrorMessage(status: number, detail?: unknown): string {
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
    return 'Terbitkan laman web anda dahulu untuk menjana kod QR.';
  }
  if (status === 503) {
    return 'Penjana kod QR tidak tersedia buat masa ini. Cuba lagi nanti.';
  }
  return 'Gagal menjana poster QR. Cuba lagi.';
}

/**
 * URL of the printable QR poster for a site.
 *
 * NOTE: this endpoint is owner-only, so the URL cannot simply be handed to
 * `window.open` — a top-level navigation carries no `Authorization` header
 * and the request comes back 401. Use `fetchPosterHtml` instead; this
 * function only builds the URL it fetches.
 */
export function qrPosterUrl(
  websiteId: string,
  opts: { table?: string; language?: 'ms' | 'en' } = {}
): string {
  const params = new URLSearchParams();
  if (opts.table) params.set('table', opts.table);
  if (opts.language) params.set('language', opts.language);
  const query = params.toString();
  return `${API_BASE}/api/v1/websites/${websiteId}/qr-poster.html${
    query ? `?${query}` : ''
  }`;
}

/**
 * Fetch the printable poster's HTML with the owner's bearer token.
 *
 * The caller renders the returned markup into a tab it opened itself. That
 * indirection is the whole point: the poster is owner-only data, so the
 * request has to be an authenticated fetch rather than a navigation. Putting
 * the token in the URL instead would leak it into browser history, referrers
 * and the server's own access logs.
 */
export async function fetchPosterHtml(
  websiteId: string,
  opts: { table?: string; language?: 'ms' | 'en' },
  token: string | null
): Promise<string> {
  const resp = await fetch(qrPosterUrl(websiteId, opts), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(qrErrorMessage(resp.status, body?.detail));
  }
  return resp.text();
}

/**
 * Black or white, whichever stays readable on `background`.
 *
 * Same WCAG relative-luminance rule the backend poster uses, so a swatch in
 * the picker is labelled the same way the printed poster labels itself.
 */
export function readableTextOn(background: string): '#111827' | '#FFFFFF' {
  const hex = normalizeHex(background);
  if (!hex) return '#111827';
  const channel = (value: number) => {
    const srgb = value / 255;
    return srgb <= 0.04045 ? srgb / 12.92 : Math.pow((srgb + 0.055) / 1.055, 2.4);
  };
  const luminance =
    0.2126 * channel(parseInt(hex.slice(1, 3), 16)) +
    0.7152 * channel(parseInt(hex.slice(3, 5), 16)) +
    0.0722 * channel(parseInt(hex.slice(5, 7), 16));
  // Contrast of white-on-bg vs black-on-bg, WCAG formula.
  const withWhite = 1.05 / (luminance + 0.05);
  const withBlack = (luminance + 0.05) / 0.05;
  return withWhite >= withBlack ? '#FFFFFF' : '#111827';
}

/** '#abc' / 'ABCDEF' -> '#AABBCC'; null when it isn't a hex colour. */
export function normalizeHex(value: string | null | undefined): string | null {
  if (!value) return null;
  let raw = String(value).trim();
  if (!raw.startsWith('#')) raw = `#${raw}`;
  if (/^#[0-9a-fA-F]{3}$/.test(raw)) {
    const [r, g, b] = [raw[1], raw[2], raw[3]];
    return `#${r}${r}${g}${g}${b}${b}`.toUpperCase();
  }
  if (/^#[0-9a-fA-F]{6}$/.test(raw)) return raw.toUpperCase();
  return null;
}

/** Is this the palette the site is already wearing? */
export function isActivePalette(
  option: PaletteOption,
  current: CurrentTheme | null
): boolean {
  if (!current) return false;
  if (current.palette_key) return current.palette_key === option.key;
  const primary = normalizeHex(current.palette?.primary);
  return !!primary && primary === normalizeHex(option.colors.primary);
}

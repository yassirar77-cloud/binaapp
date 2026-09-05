/**
 * Hero Video Background client — a GLM-generated clip behind the hero.
 *
 * The matching backend lives in `api/v1/endpoints/hero_video.py`. Two halves:
 *
 *  1. MAKING the clip is an AI call (Z.ai CogVideoX). It is asynchronous —
 *     `startHeroVideo` returns a job id at once and the panel polls
 *     `pollHeroVideoJob` every few seconds; the poll that sees the clip land
 *     stores it, patches the page and republishes in one go.
 *  2. PUTTING it on the page, adjusting the overlay, or removing it is a
 *     credit-free HTML patch: no AI, nothing else on the page moves.
 *
 * The feature is flag-gated server-side (HERO_VIDEO_ENABLED). With the flag
 * off every route 404s; `fetchHeroVideoOptions` turns that into `null` so the
 * panel can simply not render.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

export type HeroVideoOverlay = 'dark' | 'light' | 'none';
export type HeroVideoTextMode = 'auto' | 'light' | 'dark' | 'keep';

export interface HeroVideoStyle {
  key: string;
  label_ms: string;
  label_en: string;
}

export interface HeroVideoOptions {
  model: string;
  duration_seconds: number;
  durations: number[];
  poll_interval_seconds: number;
  styles: HeroVideoStyle[];
  overlays: HeroVideoOverlay[];
  text_modes: HeroVideoTextMode[];
}

export interface HeroVideoSettings {
  video_url: string;
  poster_url: string | null;
  overlay: HeroVideoOverlay;
  overlay_opacity: number;
  text_mode: HeroVideoTextMode;
  show_on_mobile: boolean;
}

export type HeroVideoJobStatus =
  | 'processing'
  | 'storing'
  | 'completed'
  | 'failed';

export interface HeroVideoJob {
  job_id: string;
  status: HeroVideoJobStatus;
  error: string | null;
  video_url: string | null;
  poster_url: string | null;
  applied: boolean;
  live_site_updated: boolean;
  elapsed_seconds: number;
  /** Present on the poll that completes the job. */
  html_content?: string;
  settings?: HeroVideoSettings;
  message?: string;
  warning?: string;
}

export interface HeroVideoState {
  has_video: boolean;
  settings: HeroVideoSettings | null;
  hero_found: boolean;
  hero_match: string;
  allowed: boolean;
  job: HeroVideoJob | null;
  poll_interval_seconds: number;
  source: string;
}

export interface HeroVideoLook {
  overlay?: HeroVideoOverlay;
  overlay_opacity?: number;
  text_mode?: HeroVideoTextMode;
  show_on_mobile?: boolean;
}

export interface StartHeroVideoRequest extends HeroVideoLook {
  style?: string;
  prompt?: string;
  duration?: number;
  image_url?: string;
}

export interface HeroVideoPatchResult {
  success: boolean;
  changed: boolean;
  message: string;
  settings?: HeroVideoSettings;
  live_site_updated: boolean;
  html_content?: string;
  warning?: string;
}

/** Malay error copy for the failure shapes the endpoints can return. */
export function heroVideoErrorMessage(status: number, detail?: unknown): string {
  if (status === 401) return 'Sesi tamat. Sila log masuk semula.';
  const code =
    detail && typeof detail === 'object' && 'error' in (detail as object)
      ? String((detail as { error: unknown }).error)
      : '';
  const message =
    detail && typeof detail === 'object' && 'message' in (detail as object)
      ? String((detail as { message: unknown }).message)
      : '';
  switch (code) {
    case 'plan_not_allowed':
      return 'Video latar hero tidak termasuk dalam pelan anda. Naik taraf untuk menggunakannya.';
    case 'hero_not_found':
      return 'Bahagian hero tidak dijumpai pada laman web ini.';
    case 'no_balanced_html_base':
      return 'Laman web ini perlu dijana semula sebelum video boleh ditambah.';
    case 'rewrite_produced_unbalanced_html':
      return 'Perubahan dibatalkan untuk melindungi laman web anda. Cuba lagi.';
    case 'job_in_progress':
      return 'Video untuk laman web ini sedang dijana. Sila tunggu.';
    case 'too_many_jobs':
      return 'Terlalu banyak video sedang dijana. Sila tunggu sebentar.';
    case 'daily_limit_reached':
      return 'Had harian video untuk laman web ini telah dicapai. Cuba lagi esok.';
    case 'video_submit_failed':
      return 'Penjanaan video gagal dimulakan. Sila cuba lagi sebentar.';
    case 'job_not_found':
      return 'Tugasan video tidak dijumpai atau telah tamat. Sila mula semula.';
    case 'no_hero_video':
      return 'Laman web ini belum ada video latar hero.';
    default:
      break;
  }
  if (message) return message;
  if (status === 403) return 'Anda tidak dibenarkan mengubah laman web ini.';
  if (status === 404) return 'Laman web tidak dijumpai.';
  if (typeof detail === 'string' && detail) return detail;
  return 'Gagal memproses video latar. Cuba lagi.';
}

/** Malay copy for a job's terminal `error` code. */
export function heroVideoJobErrorMessage(code: string | null | undefined): string {
  switch (code) {
    case 'timeout':
      return 'Penjanaan video mengambil masa terlalu lama. Sila cuba lagi.';
    case 'generation_failed':
      return 'AI gagal menjana video ini. Cuba gaya atau penerangan lain.';
    case 'storage_failed':
      return 'Video dijana tetapi gagal disimpan. Sila cuba lagi.';
    case 'hero_not_found':
      return 'Bahagian hero tidak dijumpai pada laman web ini.';
    case 'no_balanced_html_base':
      return 'Laman web ini perlu dijana semula sebelum video boleh ditambah.';
    default:
      return 'Penjanaan video gagal. Sila cuba lagi.';
  }
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

async function parseOrThrow<T>(resp: Response): Promise<T> {
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(heroVideoErrorMessage(resp.status, data?.detail));
  }
  return data as T;
}

/**
 * The style presets. Public. Returns `null` when the feature is switched
 * off server-side (404), so the panel can hide itself instead of erroring.
 */
export async function fetchHeroVideoOptions(): Promise<HeroVideoOptions | null> {
  const resp = await fetch(`${API_BASE}/api/v1/websites/hero-video/options`);
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(heroVideoErrorMessage(resp.status));
  return resp.json();
}

/** What the page has now, plus any in-flight job. */
export async function fetchHeroVideoState(
  websiteId: string,
  token: string | null
): Promise<HeroVideoState> {
  const resp = await authedFetch(`/api/v1/websites/${websiteId}/hero-video`, token);
  return parseOrThrow<HeroVideoState>(resp);
}

/** Kick off a GLM video generation. Returns the job to poll. */
export async function startHeroVideo(
  websiteId: string,
  body: StartHeroVideoRequest,
  token: string | null
): Promise<{ job_id: string; status: HeroVideoJobStatus; poll_interval_seconds: number; prompt: string; message: string }> {
  const resp = await authedFetch(
    `/api/v1/websites/${websiteId}/hero-video/generate`,
    token,
    { method: 'POST', body: JSON.stringify(body) }
  );
  return parseOrThrow(resp);
}

/** One poll. The call that sees the clip land also applies it to the page. */
export async function pollHeroVideoJob(
  websiteId: string,
  jobId: string,
  token: string | null
): Promise<HeroVideoJob> {
  const resp = await authedFetch(
    `/api/v1/websites/${websiteId}/hero-video/jobs/${jobId}`,
    token
  );
  return parseOrThrow<HeroVideoJob>(resp);
}

/** Adjust the scrim / text / mobile behaviour. Credit-free. */
export async function updateHeroVideoLook(
  websiteId: string,
  body: HeroVideoLook,
  token: string | null
): Promise<HeroVideoPatchResult> {
  const resp = await authedFetch(`/api/v1/websites/${websiteId}/hero-video`, token, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
  return parseOrThrow<HeroVideoPatchResult>(resp);
}

/** Take the video off the hero. Credit-free and exact. */
export async function removeHeroVideo(
  websiteId: string,
  token: string | null
): Promise<HeroVideoPatchResult> {
  const resp = await authedFetch(`/api/v1/websites/${websiteId}/hero-video`, token, {
    method: 'DELETE',
  });
  return parseOrThrow<HeroVideoPatchResult>(resp);
}

/** True while a job still needs polling. */
export function isHeroVideoJobActive(job: HeroVideoJob | null | undefined): boolean {
  return !!job && (job.status === 'processing' || job.status === 'storing');
}

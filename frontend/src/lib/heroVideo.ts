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
  provider?: string;
  duration_seconds: number;
  durations: number[];
  poll_interval_seconds: number;
  styles: HeroVideoStyle[];
  overlays: HeroVideoOverlay[];
  text_modes: HeroVideoTextMode[];
  /** RM per clip for accounts without free access. */
  price_rm?: number;
  /** addon_purchases.addon_type to buy one clip credit. */
  addon_type?: string;
}

/** How this account may generate: free, or by prepaid RM5 credits. */
export interface HeroVideoAccess {
  free: boolean;
  credits: number;
  allowed: boolean;
  price_rm: number;
  addon_type: string;
  /** Free (preview-only) plan: credits cannot be bought — upgrade first. */
  requires_upgrade?: boolean;
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
  /** One RM5 credit was consumed for this job; refunded if it never delivers. */
  charged?: boolean;
  refunded?: boolean;
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
  free_access?: boolean;
  credits?: number;
  price_rm?: number;
  addon_type?: string;
  requires_upgrade?: boolean;
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
    case 'payment_required':
      return 'Video latar hero berharga RM5 setiap klip. Beli 1 kredit video untuk meneruskan.';
    case 'provider_not_configured':
      return 'Penyedia video belum dikonfigurasi dengan betul di pelayan (kunci API ditolak). Sila hubungi sokongan BinaApp.';
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

/**
 * True for the errors `fetch` throws BEFORE any HTTP response exists — a
 * dropped mobile connection, a backgrounded tab, DNS, an aborted request.
 * These are worth retrying; an HTTP error the server actually sent is not.
 */
export function isTransientFetchError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  if (err.name === 'AbortError' || err.name === 'TypeError') return true;
  return /failed to fetch|networkerror|load failed|network request failed/i.test(err.message);
}

/** Malay copy for a transport failure, in place of the browser's raw text. */
export const HERO_VIDEO_CONNECTION_LOST =
  'Sambungan terputus. Video masih dijana di pelayan — kami akan cuba semula secara automatik.';

/** How many consecutive dropped polls before a job is given up on. */
export const HERO_VIDEO_MAX_POLL_FAILURES = 6;

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

/** Free access or prepaid credits for the signed-in account (no site needed). */
export async function fetchHeroVideoAccess(token: string | null): Promise<HeroVideoAccess> {
  const resp = await authedFetch('/api/v1/websites/hero-video/access', token);
  return parseOrThrow<HeroVideoAccess>(resp);
}

export const HERO_VIDEO_PENDING_RETURN_KEY = 'pending_return_to';

/**
 * Buy one hero-video credit (RM5) through the existing add-on checkout and
 * send the browser to ToyyibPay. The payment-success page reads
 * `pending_return_to` and brings the merchant back to `returnTo` (the
 * editor they came from) instead of the billing page.
 */
export async function startHeroVideoPurchase(params: {
  userId: string;
  token: string | null;
  returnTo: string;
  quantity?: number;
}): Promise<void> {
  const quantity = Math.max(1, params.quantity ?? 1);
  const resp = await fetch(`${API_BASE}/api/v1/payments/addon/purchase`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(params.token ? { Authorization: `Bearer ${params.token}` } : {}),
    },
    body: JSON.stringify({ user_id: params.userId, addon_type: 'hero_video', quantity }),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok || !data?.success || !data?.payment_url) {
    throw new Error(
      (data && typeof data.detail === 'string' && data.detail) ||
        'Gagal memulakan pembayaran. Sila cuba lagi.'
    );
  }
  try {
    localStorage.setItem('pending_payment_id', String(data.payment_id ?? ''));
    localStorage.setItem('pending_bill_code', String(data.bill_code ?? ''));
    localStorage.setItem('pending_addon_type', 'hero_video');
    localStorage.setItem('pending_addon_quantity', String(quantity));
    localStorage.setItem(HERO_VIDEO_PENDING_RETURN_KEY, params.returnTo);
    localStorage.removeItem('pending_tier');
  } catch {
    /* storage unavailable — the success page falls back to billing */
  }
  try {
    const { backupAuthState } = await import('@/lib/supabase');
    backupAuthState();
  } catch {
    /* ignore */
  }
  window.location.href = data.payment_url;
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

// ---------------------------------------------------------------------------
// Start-and-wait runner (create page)
// ---------------------------------------------------------------------------

export interface RunHeroVideoJobOptions {
  /** Called with every poll result, including the terminal one. */
  onUpdate?: (job: HeroVideoJob) => void;
  /** Return true to abandon polling (e.g. the component unmounted). */
  shouldStop?: () => boolean;
  /** Fresh token for each poll; falls back to the start token. */
  getToken?: () => Promise<string | null>;
  /** Seconds between polls; the server's poll_interval_seconds wins when set. */
  intervalSeconds?: number;
  /** Test seam — defaults to setTimeout-based sleep. */
  sleep?: (ms: number) => Promise<void>;
  /** Hard cap so a stuck job can never poll forever. */
  maxWaitSeconds?: number;
  /** Called on each dropped poll that will be retried (1-based count). */
  onTransientError?: (consecutiveFailures: number, err: unknown) => void;
}

const defaultSleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/**
 * Kick off a hero-video job and poll it to a terminal state.
 *
 * The create page has no persistent panel to resume from, so it needs the
 * whole lifecycle in one awaitable: start → poll every N seconds → return
 * the completed/failed job. The poll that observes completion carries the
 * patched `html_content`, which the caller pushes into its preview.
 *
 * Resolves with the terminal job, or `null` when `shouldStop()` asked us to
 * abandon it. Throws on a failed start or a poll transport error, with a
 * Malay message ready for the UI.
 */
export async function runHeroVideoJob(
  websiteId: string,
  body: StartHeroVideoRequest,
  token: string | null,
  opts: RunHeroVideoJobOptions = {}
): Promise<HeroVideoJob | null> {
  const started = await startHeroVideo(websiteId, body, token);
  const interval = Math.max(
    2,
    started.poll_interval_seconds || opts.intervalSeconds || 8
  );
  const sleep = opts.sleep || defaultSleep;
  const deadline = Date.now() + (opts.maxWaitSeconds ?? 600) * 1000;

  let job: HeroVideoJob = {
    job_id: started.job_id,
    status: started.status,
    error: null,
    video_url: null,
    poster_url: null,
    applied: false,
    live_site_updated: false,
    elapsed_seconds: 0,
    message: started.message,
  };
  opts.onUpdate?.(job);

  // First poll comes sooner: a 'speed' clip can land inside the first interval.
  await sleep(Math.min(interval, 3) * 1000);

  let failures = 0;
  while (isHeroVideoJobActive(job)) {
    if (opts.shouldStop?.()) return null;
    if (Date.now() > deadline) {
      job = { ...job, status: 'failed', error: 'timeout' };
      opts.onUpdate?.(job);
      return job;
    }
    const pollToken = opts.getToken ? await opts.getToken() : token;
    try {
      job = await pollHeroVideoJob(websiteId, started.job_id, pollToken);
      failures = 0;
    } catch (err) {
      // A dropped connection is not a failed job: the clip is still being
      // made server-side. Keep the job alive and poll again, a little
      // slower each time, until it is clearly not coming back.
      if (!isTransientFetchError(err) || ++failures >= HERO_VIDEO_MAX_POLL_FAILURES) throw err;
      opts.onTransientError?.(failures, err);
      await sleep(Math.min(interval * (1 + failures), 30) * 1000);
      continue;
    }
    opts.onUpdate?.(job);
    if (isHeroVideoJobActive(job)) await sleep(interval * 1000);
  }
  return job;
}

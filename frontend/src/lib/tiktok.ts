/**
 * TikTok publishing client — the admin posts to BinaApp's own account.
 *
 * Backend: `backend/app/api/v1/endpoints/tiktok.py` (paths under
 * /api/v1/social/tiktok). This module holds the fetch wrappers plus the pure
 * rules the page renders from, so the UX requirements of TikTok's Content
 * Sharing Guidelines are testable without a browser:
 *
 *  - privacy dropdown has NO default and lists only `privacy_level_options`
 *  - interaction toggles start OFF and are disabled when creator_info says so
 *  - commercial content disclosure is OFF by default; when ON at least one of
 *    "Your brand" / "Branded content" must be picked before posting
 *  - branded content can never be posted as "Only you" (SELF_ONLY)
 *  - the declaration text under the button depends on what was picked
 *
 * Uploads go to the Render backend directly (DIRECT_BACKEND_URL): the Vercel
 * proxy has a 4.5 MB body limit and a short timeout.
 */

import { DIRECT_BACKEND_URL } from '@/lib/env';
import { getApiAuthToken } from '@/lib/supabase';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || DIRECT_BACKEND_URL;
const UPLOAD_BASE = DIRECT_BACKEND_URL;
const ROOT = '/api/v1/social/tiktok';

// ---------------------------------------------------------------------------
// Types (mirror the backend views)
// ---------------------------------------------------------------------------

export type PrivacyLevel =
  | 'PUBLIC_TO_EVERYONE'
  | 'MUTUAL_FOLLOW_FRIENDS'
  | 'FOLLOWER_OF_CREATOR'
  | 'SELF_ONLY';

export interface TikTokConfig {
  configured: boolean;
  audited: boolean;
  redirect_uri: string;
  scopes: string[];
  max_upload_mb: number;
  limits: {
    video_title_max: number;
    photo_title_max: number;
    photo_description_max: number;
    max_photos: number;
  };
  photo_media_public_base: string;
  policy_links: { music_usage_confirmation: string; branded_content_policy: string };
}

export interface TikTokAccount {
  id: string;
  open_id: string;
  username: string | null;
  display_name: string | null;
  avatar_url: string | null;
  scopes: string[];
  status: 'connected' | 'reauth_required' | 'revoked';
  last_error: string | null;
  connected_at: string | null;
  access_token_expires_at: string | null;
  refresh_token_expires_at: string | null;
}

export interface CreatorInfo {
  creator_avatar_url: string | null;
  creator_username: string | null;
  creator_nickname: string | null;
  privacy_level_options: PrivacyLevel[];
  comment_disabled: boolean;
  duet_disabled: boolean;
  stitch_disabled: boolean;
  max_video_post_duration_sec: number | null;
  audited: boolean;
}

export type PostMode = 'direct' | 'inbox';
export type MediaType = 'video' | 'photo';
export type PostStatus =
  | 'queued'
  | 'uploading'
  | 'processing'
  | 'sent_to_inbox'
  | 'published'
  | 'failed';

export interface TikTokPost {
  id: string;
  mode: PostMode;
  media_type: MediaType;
  title: string | null;
  status: PostStatus;
  tiktok_status: string | null;
  fail_reason: string | null;
  error: string | null;
  publish_id: string | null;
  uploaded_bytes: number;
  total_bytes: number;
  public_post_ids: unknown;
  privacy_level: PrivacyLevel | null;
  post_info: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  finished_at: string | null;
}

/** What the composer collects; serialised into the `post` form field. */
export interface PostDraft {
  mode: PostMode;
  media_type: MediaType;
  title: string;
  description: string;
  privacy_level: PrivacyLevel | null;
  allow_comment: boolean;
  allow_duet: boolean;
  allow_stitch: boolean;
  disclose_commercial: boolean;
  your_brand: boolean;
  branded_content: boolean;
  is_aigc: boolean;
  duration_sec: number | null;
  photo_cover_index: number;
}

export const EMPTY_DRAFT: PostDraft = {
  mode: 'direct',
  media_type: 'video',
  title: '',
  description: '',
  privacy_level: null,
  allow_comment: false,
  allow_duet: false,
  allow_stitch: false,
  disclose_commercial: false,
  your_brand: false,
  branded_content: false,
  is_aigc: false,
  duration_sec: null,
  photo_cover_index: 0,
};

// ---------------------------------------------------------------------------
// Pure rules
// ---------------------------------------------------------------------------

export const PRIVACY_LABELS: Record<PrivacyLevel, string> = {
  PUBLIC_TO_EVERYONE: 'Everyone',
  MUTUAL_FOLLOW_FRIENDS: 'Friends',
  FOLLOWER_OF_CREATOR: 'Followers',
  SELF_ONLY: 'Only you',
};

export const MUSIC_USAGE_URL =
  'https://www.tiktok.com/legal/page/global/music-usage-confirmation/en';
export const BRANDED_CONTENT_POLICY_URL =
  'https://www.tiktok.com/legal/page/global/bc-policy/en';

/** Exact wording from the guidelines for the disclosure options. */
export const DISCLOSURE_COPY = {
  yourBrand: (media: MediaType) =>
    `Your ${media} will be labeled as 'Promotional content'`,
  brandedContent: (media: MediaType) =>
    `Your ${media} will be labeled as 'Paid partnership'`,
  needOne: 'You need to indicate if your content promotes yourself, a third party, or both.',
  brandedNotPrivate: 'Branded content visibility cannot be set to private.',
  processing:
    'After you post, it may take a few minutes for TikTok to process the content before it appears on the profile.',
};

/** UTF-16 code units — the unit TikTok counts caption length in. */
export function utf16Length(text: string): number {
  return text.length;
}

/** Only the options creator_info returned, in TikTok's canonical order. */
export function privacyOptions(info: CreatorInfo | null): PrivacyLevel[] {
  const order: PrivacyLevel[] = [
    'PUBLIC_TO_EVERYONE',
    'MUTUAL_FOLLOW_FRIENDS',
    'FOLLOWER_OF_CREATOR',
    'SELF_ONLY',
  ];
  const allowed = new Set(info?.privacy_level_options ?? []);
  return order.filter((o) => allowed.has(o));
}

/**
 * Whether a privacy option can be selected right now. "Only you" is greyed
 * out while Branded content is ticked (guideline: branded content cannot be
 * private).
 */
export function privacyOptionDisabled(option: PrivacyLevel, draft: PostDraft): boolean {
  return option === 'SELF_ONLY' && draft.disclose_commercial && draft.branded_content;
}

/** The mirror rule: with "Only you" selected, Branded content is unavailable. */
export function brandedContentDisabled(draft: PostDraft): boolean {
  return draft.privacy_level === 'SELF_ONLY';
}

/** The sentence under the post button, per the guidelines. */
export function declarationText(draft: PostDraft): { text: string; brandedPolicy: boolean } {
  if (draft.disclose_commercial && draft.branded_content) {
    return {
      text: "By posting, you agree to TikTok's Branded Content Policy and Music Usage Confirmation.",
      brandedPolicy: true,
    };
  }
  return { text: "By posting, you agree to TikTok's Music Usage Confirmation.", brandedPolicy: false };
}

export interface DraftCheck {
  ok: boolean;
  problems: string[];
}

/**
 * Can "Post now" be pressed? Every reason it cannot is listed so the UI can
 * show the right hint next to the disabled button.
 */
export function checkDraft(
  draft: PostDraft,
  info: CreatorInfo | null,
  limits: TikTokConfig['limits'],
  hasMedia: boolean,
): DraftCheck {
  const problems: string[] = [];
  if (!hasMedia) problems.push('Add a video or photos first.');
  if (!info) problems.push('Creator settings have not loaded yet.');

  if (draft.mode === 'direct') {
    if (!draft.privacy_level) problems.push('Choose who can view this post.');
    else if (info && !info.privacy_level_options.includes(draft.privacy_level)) {
      problems.push('That privacy option is not available for this account.');
    }
    if (draft.disclose_commercial && !draft.your_brand && !draft.branded_content) {
      problems.push(DISCLOSURE_COPY.needOne);
    }
    if (draft.disclose_commercial && draft.branded_content && draft.privacy_level === 'SELF_ONLY') {
      problems.push(DISCLOSURE_COPY.brandedNotPrivate);
    }
    const titleMax = draft.media_type === 'video' ? limits.video_title_max : limits.photo_title_max;
    if (utf16Length(draft.title) > titleMax) {
      problems.push(`Caption is over TikTok's ${titleMax} character limit.`);
    }
    if (draft.media_type === 'photo' && utf16Length(draft.description) > limits.photo_description_max) {
      problems.push(`Description is over TikTok's ${limits.photo_description_max} character limit.`);
    }
  }

  if (
    draft.media_type === 'video' &&
    draft.duration_sec != null &&
    info?.max_video_post_duration_sec &&
    draft.duration_sec > info.max_video_post_duration_sec
  ) {
    problems.push(
      `Video is ${Math.round(draft.duration_sec)}s; this account can post up to ${info.max_video_post_duration_sec}s.`,
    );
  }
  return { ok: problems.length === 0, problems };
}

/** The JSON the backend's PostRequest expects. */
export function toPostRequest(draft: PostDraft): Record<string, unknown> {
  const disclose = draft.mode === 'direct' && draft.disclose_commercial;
  return {
    mode: draft.mode,
    media_type: draft.media_type,
    title: draft.title,
    description: draft.description,
    privacy_level: draft.mode === 'direct' ? draft.privacy_level : null,
    disable_comment: !draft.allow_comment,
    disable_duet: !draft.allow_duet,
    disable_stitch: !draft.allow_stitch,
    brand_organic_toggle: disclose && draft.your_brand,
    brand_content_toggle: disclose && draft.branded_content,
    is_aigc: draft.is_aigc,
    duration_sec: draft.duration_sec,
    photo_cover_index: draft.photo_cover_index,
  };
}

export function isPostActive(post: TikTokPost | null): boolean {
  return !!post && (post.status === 'queued' || post.status === 'uploading' || post.status === 'processing');
}

export function describeStatus(post: TikTokPost): { label: string; tone: 'info' | 'ok' | 'err' } {
  switch (post.status) {
    case 'queued':
      return { label: 'Queued', tone: 'info' };
    case 'uploading': {
      const pct = post.total_bytes ? Math.round((post.uploaded_bytes / post.total_bytes) * 100) : 0;
      return { label: `Uploading to TikTok… ${pct}%`, tone: 'info' };
    }
    case 'processing':
      return { label: 'Processing on TikTok…', tone: 'info' };
    case 'sent_to_inbox':
      return { label: 'Sent to TikTok drafts — open the TikTok app inbox to finish', tone: 'ok' };
    case 'published':
      return {
        label:
          post.privacy_level === 'SELF_ONLY'
            ? 'Posted (visible only to you)'
            : `Posted (${post.privacy_level ? PRIVACY_LABELS[post.privacy_level] : 'live'})`,
        tone: 'ok',
      };
    case 'failed':
    default:
      return { label: post.error || 'Failed', tone: 'err' };
  }
}

// ---------------------------------------------------------------------------
// Fetch wrappers
// ---------------------------------------------------------------------------

export class TikTokApiError extends Error {
  status: number;
  code: string | null;
  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = 'TikTokApiError';
    this.status = status;
    this.code = code;
  }
}

/** Pull `{detail: {error, message}}`, `{detail: "..."}` or `{message}` out of an error body. */
export function errorFromBody(status: number, body: unknown): TikTokApiError {
  const b = (body ?? {}) as Record<string, unknown>;
  const detail = b.detail as unknown;
  if (detail && typeof detail === 'object') {
    const d = detail as Record<string, unknown>;
    return new TikTokApiError(
      String(d.message ?? d.error ?? `Request failed (${status})`),
      status,
      typeof d.error === 'string' ? d.error : null,
    );
  }
  if (typeof detail === 'string') return new TikTokApiError(detail, status);
  if (typeof b.message === 'string') return new TikTokApiError(b.message, status);
  return new TikTokApiError(`Request failed (${status})`, status);
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getApiAuthToken();
  if (!token) throw new TikTokApiError('Not signed in', 401, 'not_authenticated');
  return { Authorization: `Bearer ${token}` };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(await authHeaders()),
    ...(init.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    ...((init.headers as Record<string, string>) || {}),
  };
  const res = await fetch(`${API_BASE}${ROOT}${path}`, { ...init, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw errorFromBody(res.status, body);
  return body as T;
}

export const fetchTikTokConfig = () => request<TikTokConfig>('/config');

export const fetchTikTokAccount = (refresh = false) =>
  request<{ connected: boolean; account: TikTokAccount | null }>(
    `/account${refresh ? '?refresh=true' : ''}`,
  );

export const startTikTokOAuth = () =>
  request<{ authorize_url: string; redirect_uri: string }>('/oauth/start', { method: 'POST' });

export const completeTikTokOAuth = (code: string, state: string) =>
  request<{ connected: boolean; account: TikTokAccount }>('/oauth/callback', {
    method: 'POST',
    body: JSON.stringify({ code, state }),
  });

export const disconnectTikTok = () =>
  request<{ disconnected: boolean; revoked: boolean }>('/account', { method: 'DELETE' });

export const fetchCreatorInfo = () => request<CreatorInfo>('/creator-info');

export const draftTikTokCaption = (brief: string, language: 'ms' | 'en' | 'mixed', media: MediaType) =>
  request<{ caption: string; provider: string }>('/caption', {
    method: 'POST',
    body: JSON.stringify({ brief, language, media_type: media }),
  });

export const fetchTikTokPosts = (limit = 10) =>
  request<{ posts: TikTokPost[] }>(`/posts?limit=${limit}`);

export const fetchTikTokPost = (id: string) => request<{ post: TikTokPost }>(`/posts/${id}`);

/**
 * Upload the media and start the publish. Uses XHR so the admin sees upload
 * progress for large videos; the JSON contract matches `request()`.
 */
export function createTikTokPost(
  draft: PostDraft,
  files: File[],
  onProgress?: (fraction: number) => void,
): Promise<{ post: TikTokPost; processing_notice: string }> {
  return new Promise((resolve, reject) => {
    authHeaders()
      .then((headers) => {
        const form = new FormData();
        form.append('post', JSON.stringify(toPostRequest(draft)));
        files.forEach((f) => form.append('files', f, f.name));

        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${UPLOAD_BASE}${ROOT}/posts`);
        Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable && onProgress) onProgress(ev.loaded / ev.total);
        };
        xhr.onerror = () => reject(new TikTokApiError('Upload failed (network)', 0, 'network'));
        xhr.onload = () => {
          let body: unknown = {};
          try {
            body = JSON.parse(xhr.responseText || '{}');
          } catch {
            body = {};
          }
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(body as { post: TikTokPost; processing_notice: string });
          } else {
            reject(errorFromBody(xhr.status, body));
          }
        };
        xhr.send(form);
      })
      .catch(reject);
  });
}

/** Read a video file's duration in the browser (null when unreadable). */
export function probeVideoDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    if (typeof document === 'undefined') return resolve(null);
    const url = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.preload = 'metadata';
    const done = (value: number | null) => {
      URL.revokeObjectURL(url);
      resolve(value);
    };
    video.onloadedmetadata = () => done(Number.isFinite(video.duration) ? video.duration : null);
    video.onerror = () => done(null);
    video.src = url;
  });
}

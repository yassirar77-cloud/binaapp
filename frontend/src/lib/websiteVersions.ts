/**
 * Version history client — earlier copies of a page, and putting one back.
 *
 * The matching backend lives in `api/v1/endpoints/website_versions.py`.
 * Every change that overwrites a page (editor save, AI regenerate, theme,
 * contact, hero video) first stores the page as it was. Restoring one is
 * credit-free and is itself undoable: the page being replaced is stored as a
 * new version before the old one goes back.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

export type VersionSource =
  | 'manual_save'
  | 'regenerate'
  | 'theme'
  | 'contact'
  | 'hero_video'
  | 'restore'
  | 'publish';

export interface WebsiteVersion {
  id: string;
  website_id: string;
  source: VersionSource | string;
  label: string | null;
  size_bytes: number;
  created_at: string;
}

export interface RestoreResult {
  success: boolean;
  changed: boolean;
  message: string;
  live_site_updated: boolean;
  html_content: string;
  undo_version_id?: string | null;
  warning?: string;
}

/** A version is the page BEFORE the change named by its source. */
const SOURCE_LABELS: Record<string, string> = {
  manual_save: 'Sebelum simpanan editor',
  regenerate: 'Sebelum jana semula AI',
  theme: 'Sebelum tukar tema',
  contact: 'Sebelum tukar nombor WhatsApp',
  hero_video: 'Sebelum ubah video latar',
  restore: 'Sebelum pemulihan versi',
  publish: 'Sebelum terbit',
};

export function versionSourceLabel(source: string): string {
  return SOURCE_LABELS[source] || 'Versi terdahulu';
}

/** "14 Nov 2026, 3:05 PTG" in Malay; the raw string if it cannot be parsed. */
export function formatVersionTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('ms-MY', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function formatVersionSize(bytes: number): string {
  if (!bytes || bytes < 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  return `${Math.round(bytes / 1024)} KB`;
}

/** Malay error copy for the failure shapes the endpoints can return. */
export function versionErrorMessage(status: number, detail?: unknown): string {
  if (status === 401 || status === 403) {
    return 'Sesi tamat. Sila log masuk semula.';
  }
  const obj =
    detail && typeof detail === 'object'
      ? (detail as { error?: unknown; message?: unknown })
      : null;
  const code = obj?.error ? String(obj.error) : '';
  if (code === 'version_not_found') return 'Versi ini tidak ditemui lagi.';
  if (code === 'version_html_unbalanced') {
    return 'Versi ini tidak lengkap dan tidak boleh dipulihkan.';
  }
  if (code === 'generation_in_progress') {
    return 'Laman web sedang dijana. Sila tunggu sehingga siap.';
  }
  if (status === 404) return 'Laman web tidak dijumpai.';
  if (obj?.message) return String(obj.message);
  if (typeof detail === 'string' && detail) return detail;
  return 'Sejarah versi tidak dapat dimuatkan. Cuba lagi.';
}

async function request<T>(
  path: string,
  token: string | null,
  init?: RequestInit
): Promise<T> {
  const resp = await fetch(`${API_BASE}/api/v1/websites/${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(versionErrorMessage(resp.status, data?.detail));
  return data as T;
}

export async function fetchVersions(
  websiteId: string,
  token: string | null
): Promise<WebsiteVersion[]> {
  const data = await request<{ versions?: WebsiteVersion[] }>(
    `${websiteId}/versions`,
    token
  );
  return data.versions || [];
}

export async function fetchVersionHtml(
  websiteId: string,
  versionId: string,
  token: string | null
): Promise<string> {
  const data = await request<{ html_content?: string }>(
    `${websiteId}/versions/${versionId}`,
    token
  );
  return data.html_content || '';
}

export async function restoreVersion(
  websiteId: string,
  versionId: string,
  token: string | null
): Promise<RestoreResult> {
  return request<RestoreResult>(
    `${websiteId}/versions/${versionId}/restore`,
    token,
    { method: 'POST' }
  );
}

export async function labelVersion(
  websiteId: string,
  versionId: string,
  label: string,
  token: string | null
): Promise<WebsiteVersion> {
  const data = await request<{ version: WebsiteVersion }>(
    `${websiteId}/versions/${versionId}`,
    token,
    { method: 'PATCH', body: JSON.stringify({ label }) }
  );
  return data.version;
}

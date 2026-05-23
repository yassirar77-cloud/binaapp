/**
 * Helpers for the regenerate polling UX in the editor.
 *
 * Backend AI budget (ai_service.py): AI_PRIMARY_TIMEOUT_SECONDS=120s
 * + AI_FALLBACK_TIMEOUT_SECONDS=90s = 210s worst case. Frontend poll
 * timeout is sized to that + 30s buffer for HTTP/DB overhead, and is
 * configurable via NEXT_PUBLIC_REGENERATE_POLL_TIMEOUT_MS.
 *
 * Pure functions only — no React, no fetch. The editor page wires them
 * to its interval + state.
 */

export const REGENERATE_POLL_INTERVAL_MS = 3000;
export const REGENERATE_POLL_DEFAULT_TIMEOUT_MS = 240_000;
export const REGENERATE_POLL_AUTO_REFRESH_DELAY_MS = 30_000;

export const REGENERATE_TIMEOUT_MESSAGE =
  'Regenerate masih dalam proses di belakang. Sila refresh halaman dalam 1 minit untuk lihat hasil.';

/**
 * Read NEXT_PUBLIC_REGENERATE_POLL_TIMEOUT_MS from process.env and clamp
 * to a sane range. Falls back to the default if unset, non-numeric, or
 * below the backend budget (210s).
 */
export function resolvePollTimeoutMs(
  raw: string | undefined = process.env.NEXT_PUBLIC_REGENERATE_POLL_TIMEOUT_MS
): number {
  if (!raw) return REGENERATE_POLL_DEFAULT_TIMEOUT_MS;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return REGENERATE_POLL_DEFAULT_TIMEOUT_MS;
  }
  // Don't allow the frontend to give up before the backend's 210s budget.
  const MIN_TIMEOUT_MS = 210_000;
  return Math.max(MIN_TIMEOUT_MS, Math.floor(parsed));
}

/**
 * Pick the progressive loading message shown while polling for the
 * regenerate result. Bands are inclusive-lower / exclusive-upper, so
 * `elapsedMs = 60000` flips to the second band.
 *
 * Negative or non-finite input is treated as 0 (defensive — elapsed
 * time is derived from Date.now() subtraction which could be off after
 * clock skew or test mocks).
 */
export function pickRegenerateLoadingMessage(elapsedMs: number): string {
  const elapsed =
    Number.isFinite(elapsedMs) && elapsedMs > 0 ? Math.floor(elapsedMs) : 0;
  if (elapsed < 60_000) return 'Menjana laman web baru...';
  if (elapsed < 120_000) return 'Masih menjana... AI sedang kerja keras.';
  if (elapsed < 180_000) return 'Hampir siap... cuba kaedah lain.';
  return 'Hampir siap... mohon sabar.';
}

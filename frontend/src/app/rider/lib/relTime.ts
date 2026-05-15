// Relative-time formatter in Malay. Duplicated from /pesanan/lib/relTime.ts
// so the rider PWA is self-contained (it can be bundled independently for
// the service worker scope).

const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

export function relTime(iso: string, now: number = Date.now()): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '';
  const diff = Math.max(0, now - t);

  if (diff < MIN) return 'baru sahaja';
  if (diff < HOUR) {
    const m = Math.floor(diff / MIN);
    return `${m} min lalu`;
  }
  if (diff < DAY) {
    const h = Math.floor(diff / HOUR);
    const m = Math.floor((diff - h * HOUR) / MIN);
    return m > 0 ? `${h}j ${m}m lalu` : `${h}j lalu`;
  }
  const d = Math.floor(diff / DAY);
  return `${d} hari lalu`;
}

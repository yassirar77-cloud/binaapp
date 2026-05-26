/**
 * Progressive loading messages shown while a full regenerate is running.
 *
 * The regenerate job is async on the backend: the editor kicks it off
 * then polls GET /:id every few seconds. A full rebuild typically takes
 * 1–3 minutes, so a single static "loading…" string feels broken. These
 * thresholds rotate the copy as the wait grows so the user knows it's
 * still working.
 *
 * Pure module (no React) so the threshold logic is unit-testable.
 */

export interface PollMessage {
  /** Minimum elapsed time (ms) before this message applies. */
  thresholdMs: number;
  /** Bahasa Melayu copy shown to the user. */
  text: string;
}

export const POLL_MESSAGES: readonly PollMessage[] = [
  { thresholdMs: 0, text: 'Menjana laman web baru...' },
  { thresholdMs: 60_000, text: 'Masih menjana... AI sedang kerja keras.' },
  { thresholdMs: 120_000, text: 'Hampir siap... cuba kaedah lain.' },
  { thresholdMs: 180_000, text: 'Hampir siap... mohon sabar.' },
] as const;

/**
 * Pick the message for a given elapsed time. Returns the text of the
 * last threshold that the elapsed time has passed. Negative / non-finite
 * inputs clamp to the first message.
 */
export function pollMessageForElapsed(elapsedMs: number): string {
  const ms = Number.isFinite(elapsedMs) ? elapsedMs : 0;
  let current = POLL_MESSAGES[0].text;
  for (const m of POLL_MESSAGES) {
    if (ms >= m.thresholdMs) current = m.text;
  }
  return current;
}

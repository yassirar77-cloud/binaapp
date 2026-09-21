/**
 * Liveness rules for polling a website-generation job.
 *
 * The create page used to give up after a fixed 200 polls (10 minutes)
 * regardless of what the backend was reporting. A full pipeline run —
 * five AI images, a design plan, the HTML model, the critique gate, the
 * polish passes, validation — routinely takes longer than that, and the
 * job that prompted this file (44294844) was still progressing when the
 * page declared it dead; the backend completed it one minute later and
 * the merchant never saw the site.
 *
 * The question is not "how long has it been?" but "is anyone still
 * working on this job?". The backend answers that through the job row:
 * progress moves at each step and `updated_at` is touched by a heartbeat
 * while the task is alive. So the page keeps polling for as long as the
 * row keeps changing, and gives up only when it has been silent for
 * STALL_MS (the worker died — a redeploy, a crash) or when a hard ceiling
 * has passed (something is wrong even if the row is still twitching).
 *
 * Pure module (no React, no fetch) so the rules are unit-testable.
 */

/** Poll cadence. */
export const GENERATION_POLL_INTERVAL_MS = 3_000;

/**
 * No change in status, progress or updated_at for this long means the
 * worker is gone. The backend heartbeat writes updated_at every 30s and
 * the longest single bounded AI call is 5 minutes, so 6 minutes of
 * silence is a dead task, not a slow one.
 */
export const GENERATION_STALL_MS = 6 * 60_000;

/**
 * Absolute ceiling for one generation, live or not. A full run is 9–15
 * minutes today; twice that is a fault, not a slow day.
 */
export const GENERATION_HARD_CAP_MS = 30 * 60_000;

export interface PollSample {
  status?: string | null;
  progress?: number | null;
  /** The job row's updated_at as the backend returned it (opaque string). */
  updated_at?: string | null;
}

export interface PollLiveness {
  /** Wall-clock (ms) of the last poll whose sample differed from the previous one. */
  lastChangeAt: number;
  /** Fingerprint of the last sample, so a repeat is recognisable. */
  signature: string;
  /** Last progress percentage seen, for the timeout message. */
  progress: number;
}

export type PollVerdict = 'continue' | 'stalled' | 'exceeded';

export function initialLiveness(now: number): PollLiveness {
  return { lastChangeAt: now, signature: '', progress: 0 };
}

function signatureOf(sample: PollSample): string {
  return `${sample.status ?? ''}|${sample.progress ?? ''}|${sample.updated_at ?? ''}`;
}

/**
 * Fold a poll response into the liveness record. Any change in status,
 * progress or updated_at counts as a sign of life. A poll that failed
 * (no sample) leaves the record untouched, so a dead network eventually
 * stalls out the same way a dead worker does.
 */
export function observePoll(prev: PollLiveness, sample: PollSample | null, now: number): PollLiveness {
  if (!sample) return prev;
  const signature = signatureOf(sample);
  const progress = typeof sample.progress === 'number' && Number.isFinite(sample.progress)
    ? sample.progress
    : prev.progress;
  if (signature === prev.signature) {
    return { ...prev, progress };
  }
  return { lastChangeAt: now, signature, progress };
}

/**
 * A tick that arrives this long after the previous one means the browser
 * suspended the page in between (screen off, app switched: Android stops
 * a background tab's timers outright). Nothing was observed during that
 * gap, so it cannot count as silence from the server.
 */
export const GENERATION_SLEEP_GAP_MS = 4 * GENERATION_POLL_INTERVAL_MS;

/**
 * Apply at the start of a tick, before polling. After a sleep the stall
 * window restarts from now: the row is judged on what the next polls
 * return, not on the time the page spent asleep. Job 25bff45b: the page
 * slept from 44% through completion, woke twelve minutes later and
 * declared the job stalled before asking the server once.
 */
export function afterSleep(liveness: PollLiveness, lastTickAt: number, now: number): PollLiveness {
  if (now - lastTickAt < GENERATION_SLEEP_GAP_MS) return liveness;
  return { ...liveness, lastChangeAt: now };
}

/**
 * Decide whether to keep polling. Checked AFTER each poll has been folded
 * in, never before: a page that wakes to find the job completed must see
 * the site, not a stall message.
 */
export function pollVerdict(liveness: PollLiveness, startedAt: number, now: number): PollVerdict {
  if (now - startedAt >= GENERATION_HARD_CAP_MS) return 'exceeded';
  if (now - liveness.lastChangeAt >= GENERATION_STALL_MS) return 'stalled';
  return 'continue';
}

/** The error shown in the modal when polling gives up. */
export function pollGiveUpMessage(verdict: Exclude<PollVerdict, 'continue'>, liveness: PollLiveness, jobId: string): string {
  const job = jobId.slice(0, 8);
  const at = liveness.progress > 0 ? ` (stuck at ${liveness.progress}%)` : '';
  if (verdict === 'exceeded') {
    return `Generation is taking longer than ${GENERATION_HARD_CAP_MS / 60_000} minutes${at}. Job: ${job}. Please try again.`;
  }
  return `Generation stalled: no update from the server for ${GENERATION_STALL_MS / 60_000} minutes${at}. Job: ${job}. Please try again.`;
}

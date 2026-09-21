import { describe, it, expect } from 'vitest';
import {
  GENERATION_HARD_CAP_MS,
  GENERATION_POLL_INTERVAL_MS,
  GENERATION_SLEEP_GAP_MS,
  GENERATION_STALL_MS,
  afterSleep,
  initialLiveness,
  observePoll,
  pollGiveUpMessage,
  pollVerdict,
} from './generationPoll';

const MIN = 60_000;

describe('generation polling liveness', () => {
  it('keeps polling for as long as the job row keeps changing, past the old 10-minute cap', () => {
    // Job 44294844: progress 25% for 5.5 min of image generation, 55% for
    // 6 min of HTML generation, 75% for 3.5 min of polish + validation,
    // completed at 15 min. Every window is shorter than the stall limit,
    // so a page that watches the row never gives up on it.
    const t0 = 1_000_000;
    let live = initialLiveness(t0);
    const samples: Array<[number, number, string]> = [
      [0, 20, 'a'], [0.1, 25, 'b'],
      [5.5, 55, 'c'],
      [11.5, 75, 'd'],
      [12.5, 78, 'e'], [13.5, 80, 'f'], [14.5, 92, 'g'],
    ];
    let next = 0;
    for (let minute = 0; minute <= 15; minute += 0.05) {
      const now = t0 + minute * MIN;
      expect(pollVerdict(live, t0, now)).toBe('continue');
      while (next < samples.length && samples[next][0] <= minute) {
        const [, progress, updated_at] = samples[next++];
        live = observePoll(live, { status: 'processing', progress, updated_at }, now);
      }
    }
    expect(live.progress).toBe(92);
  });

  it('a heartbeat that only touches updated_at counts as a sign of life', () => {
    const t0 = 0;
    let live = initialLiveness(t0);
    live = observePoll(live, { status: 'processing', progress: 75, updated_at: '10:00:00' }, t0);
    // Same progress for 9 minutes, but updated_at moves every 30s.
    for (let s = 30; s <= 9 * 60; s += 30) {
      const now = t0 + s * 1000;
      expect(pollVerdict(live, t0, now)).toBe('continue');
      live = observePoll(live, { status: 'processing', progress: 75, updated_at: `10:${s}` }, now);
    }
    expect(pollVerdict(live, t0, t0 + 9 * MIN)).toBe('continue');
  });

  it('gives up when the row stops changing for the stall window (dead worker)', () => {
    const t0 = 0;
    let live = initialLiveness(t0);
    live = observePoll(live, { status: 'processing', progress: 75, updated_at: 'x' }, t0);
    const silentSince = t0 + 2 * MIN;
    live = observePoll(live, { status: 'processing', progress: 75, updated_at: 'y' }, silentSince);
    // Identical samples from here on.
    for (let s = 3; s < GENERATION_STALL_MS / 1000; s += 3) {
      const now = silentSince + s * 1000;
      expect(pollVerdict(live, t0, now)).toBe('continue');
      live = observePoll(live, { status: 'processing', progress: 75, updated_at: 'y' }, now);
    }
    expect(pollVerdict(live, t0, silentSince + GENERATION_STALL_MS)).toBe('stalled');
  });

  it('failed polls do not count as life, so a dead network stalls out too', () => {
    const t0 = 0;
    let live = initialLiveness(t0);
    live = observePoll(live, null, t0 + MIN);
    live = observePoll(live, null, t0 + 3 * MIN);
    expect(live.lastChangeAt).toBe(t0);
    expect(pollVerdict(live, t0, t0 + GENERATION_STALL_MS)).toBe('stalled');
  });

  it('enforces the hard ceiling even while the row is still changing', () => {
    const t0 = 0;
    let live = initialLiveness(t0);
    const justUnder = t0 + GENERATION_HARD_CAP_MS - 1000;
    live = observePoll(live, { status: 'processing', progress: 50, updated_at: 'fresh' }, justUnder);
    expect(pollVerdict(live, t0, justUnder)).toBe('continue');
    expect(pollVerdict(live, t0, t0 + GENERATION_HARD_CAP_MS)).toBe('exceeded');
  });

  it('a page that slept through the job is judged on what it sees when it wakes', () => {
    // Job 25bff45b: last poll at 44% (~4 min in), the phone suspended the
    // page, the backend completed the job, the page woke 12 minutes later.
    const t0 = 0;
    let live = initialLiveness(t0);
    const lastTick = t0 + 4 * MIN;
    live = observePoll(live, { status: 'processing', progress: 44, updated_at: 'a' }, lastTick);
    const wake = lastTick + 12 * MIN;

    // Judged before polling, the old order: a stall, wrongly.
    expect(pollVerdict(live, t0, wake)).toBe('stalled');

    // The sleep gap restarts the window, and the poll then shows the job done.
    live = afterSleep(live, lastTick, wake);
    expect(pollVerdict(live, t0, wake)).toBe('continue');
    live = observePoll(live, { status: 'completed', progress: 100, updated_at: 'z' }, wake);
    expect(live.progress).toBe(100);
    expect(pollVerdict(live, t0, wake)).toBe('continue');

    // A worker that really died is still caught: identical rows for a
    // full window after waking.
    let dead = afterSleep(initialLiveness(t0), lastTick, wake);
    for (let s = 0; s < GENERATION_STALL_MS / 1000; s += 3) {
      dead = observePoll(dead, { status: 'processing', progress: 44, updated_at: 'a' }, wake + s * 1000);
    }
    expect(pollVerdict(dead, t0, wake + GENERATION_STALL_MS)).toBe('stalled');
  });

  it('an ordinary tick gap is not a sleep', () => {
    let live = initialLiveness(0);
    live = observePoll(live, { status: 'processing', progress: 30, updated_at: 'a' }, 1000);
    const later = 1000 + GENERATION_SLEEP_GAP_MS - 1;
    expect(afterSleep(live, 1000 + GENERATION_POLL_INTERVAL_MS, later)).toEqual(live);
    expect(afterSleep(live, 1000, 1000 + GENERATION_SLEEP_GAP_MS).lastChangeAt).toBe(1000 + GENERATION_SLEEP_GAP_MS);
  });

  it('remembers the last progress for the message even when nothing else changed', () => {
    let live = initialLiveness(0);
    live = observePoll(live, { status: 'processing', progress: 55, updated_at: 'a' }, 1);
    live = observePoll(live, { status: 'processing', progress: 55, updated_at: 'a' }, 2);
    expect(live.progress).toBe(55);
    expect(pollGiveUpMessage('stalled', live, '44294844-580c-4bff')).toBe(
      'Generation stalled: no update from the server for 6 minutes (stuck at 55%). Job: 44294844. Please try again.'
    );
    expect(pollGiveUpMessage('exceeded', initialLiveness(0), '44294844-580c-4bff')).toBe(
      'Generation is taking longer than 30 minutes. Job: 44294844. Please try again.'
    );
  });
});

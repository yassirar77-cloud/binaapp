import { describe, it, expect } from 'vitest';
import { pollMessageForElapsed, POLL_MESSAGES } from './regeneratePollMessages';

describe('pollMessageForElapsed', () => {
  it('shows the first message at the start', () => {
    expect(pollMessageForElapsed(0)).toBe('Menjana laman web baru...');
    expect(pollMessageForElapsed(1_000)).toBe('Menjana laman web baru...');
  });

  it('advances after 60s', () => {
    expect(pollMessageForElapsed(60_000)).toBe(
      'Masih menjana... AI sedang kerja keras.'
    );
    expect(pollMessageForElapsed(119_999)).toBe(
      'Masih menjana... AI sedang kerja keras.'
    );
  });

  it('advances after 120s', () => {
    expect(pollMessageForElapsed(120_000)).toBe('Hampir siap... cuba kaedah lain.');
  });

  it('advances after 180s', () => {
    expect(pollMessageForElapsed(180_000)).toBe('Hampir siap... mohon sabar.');
    expect(pollMessageForElapsed(999_999)).toBe('Hampir siap... mohon sabar.');
  });

  it('clamps negative / non-finite input to the first message', () => {
    expect(pollMessageForElapsed(-5)).toBe('Menjana laman web baru...');
    expect(pollMessageForElapsed(NaN)).toBe('Menjana laman web baru...');
  });

  it('exposes four ascending thresholds', () => {
    expect(POLL_MESSAGES).toHaveLength(4);
    for (let i = 1; i < POLL_MESSAGES.length; i++) {
      expect(POLL_MESSAGES[i].thresholdMs).toBeGreaterThan(
        POLL_MESSAGES[i - 1].thresholdMs
      );
    }
  });
});

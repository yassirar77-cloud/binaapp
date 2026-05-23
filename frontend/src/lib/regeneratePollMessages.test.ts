import { describe, it, expect } from 'vitest';
import {
  pickRegenerateLoadingMessage,
  resolvePollTimeoutMs,
  REGENERATE_POLL_DEFAULT_TIMEOUT_MS,
  REGENERATE_TIMEOUT_MESSAGE,
} from './regeneratePollMessages';

describe('pickRegenerateLoadingMessage', () => {
  it('shows the initial message at t=0', () => {
    expect(pickRegenerateLoadingMessage(0)).toBe('Menjana laman web baru...');
  });

  it('keeps the initial message just below 60s', () => {
    expect(pickRegenerateLoadingMessage(59_999)).toBe(
      'Menjana laman web baru...'
    );
  });

  it('flips to the AI-working message at exactly 60s', () => {
    expect(pickRegenerateLoadingMessage(60_000)).toBe(
      'Masih menjana... AI sedang kerja keras.'
    );
  });

  it('stays on the AI-working message just below 120s', () => {
    expect(pickRegenerateLoadingMessage(119_999)).toBe(
      'Masih menjana... AI sedang kerja keras.'
    );
  });

  it('flips to the "trying another method" message at 120s', () => {
    expect(pickRegenerateLoadingMessage(120_000)).toBe(
      'Hampir siap... cuba kaedah lain.'
    );
  });

  it('flips to the final patience message at 180s', () => {
    expect(pickRegenerateLoadingMessage(180_000)).toBe(
      'Hampir siap... mohon sabar.'
    );
  });

  it('keeps the final message past 240s (until poll timeout fires)', () => {
    expect(pickRegenerateLoadingMessage(239_999)).toBe(
      'Hampir siap... mohon sabar.'
    );
    expect(pickRegenerateLoadingMessage(10 * 60_000)).toBe(
      'Hampir siap... mohon sabar.'
    );
  });

  it('treats negative or non-finite input as t=0', () => {
    expect(pickRegenerateLoadingMessage(-1)).toBe('Menjana laman web baru...');
    expect(pickRegenerateLoadingMessage(NaN)).toBe(
      'Menjana laman web baru...'
    );
    expect(pickRegenerateLoadingMessage(Infinity)).toBe(
      'Menjana laman web baru...'
    );
  });
});

describe('resolvePollTimeoutMs', () => {
  it('falls back to default when env var is unset', () => {
    expect(resolvePollTimeoutMs(undefined)).toBe(
      REGENERATE_POLL_DEFAULT_TIMEOUT_MS
    );
  });

  it('falls back to default for empty string', () => {
    expect(resolvePollTimeoutMs('')).toBe(REGENERATE_POLL_DEFAULT_TIMEOUT_MS);
  });

  it('falls back to default for non-numeric input', () => {
    expect(resolvePollTimeoutMs('not-a-number')).toBe(
      REGENERATE_POLL_DEFAULT_TIMEOUT_MS
    );
  });

  it('falls back to default for zero or negative input', () => {
    expect(resolvePollTimeoutMs('0')).toBe(REGENERATE_POLL_DEFAULT_TIMEOUT_MS);
    expect(resolvePollTimeoutMs('-5000')).toBe(
      REGENERATE_POLL_DEFAULT_TIMEOUT_MS
    );
  });

  it('honours a custom value above the backend budget', () => {
    expect(resolvePollTimeoutMs('300000')).toBe(300_000);
  });

  it('clamps values below the 210s backend budget up to the floor', () => {
    expect(resolvePollTimeoutMs('60000')).toBe(210_000);
  });

  it('returns 240000 as the documented default', () => {
    expect(REGENERATE_POLL_DEFAULT_TIMEOUT_MS).toBe(240_000);
  });
});

describe('REGENERATE_TIMEOUT_MESSAGE', () => {
  it('is the softer Bahasa Melayu message that tells the user to refresh in ~1 minute', () => {
    expect(REGENERATE_TIMEOUT_MESSAGE).toBe(
      'Regenerate masih dalam proses di belakang. Sila refresh halaman dalam 1 minit untuk lihat hasil.'
    );
  });
});

import { describe, expect, it } from 'vitest';

import { cleanPhoneDigits, formatPhoneForWA } from './phone';

describe('formatPhoneForWA', () => {
  it('adds the MY country code to local numbers', () => {
    expect(formatPhoneForWA('0123456789')).toBe('60123456789');
    expect(formatPhoneForWA('012-345 6789')).toBe('60123456789');
  });

  it('is idempotent for numbers already starting with 60', () => {
    expect(formatPhoneForWA('60123456789')).toBe('60123456789');
    expect(formatPhoneForWA('+60 12-345 6789')).toBe('60123456789');
  });

  it('treats bare numbers without leading 0 as MY', () => {
    expect(formatPhoneForWA('123456789')).toBe('60123456789');
  });

  it('returns empty for empty/undefined input', () => {
    expect(formatPhoneForWA('')).toBe('');
    expect(formatPhoneForWA(null)).toBe('');
    expect(formatPhoneForWA(undefined)).toBe('');
  });
});

describe('cleanPhoneDigits', () => {
  it('strips everything but digits', () => {
    expect(cleanPhoneDigits('+60 12-345 6789')).toBe('60123456789');
    expect(cleanPhoneDigits(null)).toBe('');
  });
});

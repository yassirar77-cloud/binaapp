import { describe, it, expect } from 'vitest';
import { normalizePriceInput } from './priceInput';

describe('normalizePriceInput', () => {
  it('leaves a clean price alone', () => {
    expect(normalizePriceInput('24.90')).toBe('24.90');
    expect(normalizePriceInput('5')).toBe('5');
    expect(normalizePriceInput(' 16.90 ')).toBe('16.90');
  });

  it('settles a dangling separator', () => {
    expect(normalizePriceInput('24.')).toBe('24');
    expect(normalizePriceInput('.9')).toBe('0.9');
    expect(normalizePriceInput('12,')).toBe('12');
  });

  it('treats a bare separator or nothing as no price', () => {
    expect(normalizePriceInput('.')).toBe('');
    expect(normalizePriceInput('')).toBe('');
    expect(normalizePriceInput(null)).toBe('');
    expect(normalizePriceInput(undefined)).toBe('');
  });
});

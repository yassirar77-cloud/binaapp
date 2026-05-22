import { describe, it, expect } from 'vitest';
import { buildRegenerateWarning } from './regenerateWarning';

describe('buildRegenerateWarning', () => {
  describe('when no uploaded photos', () => {
    it('returns the soft warning with no acknowledgement gate', () => {
      const w = buildRegenerateWarning(0);
      expect(w.hasUploadedImages).toBe(false);
      expect(w.requiresAcknowledge).toBe(false);
      expect(w.checkboxLabel).toBe('');
      // The legacy phrasing — explicit so a regression that quietly
      // drops the warning fails this test.
      expect(w.body).toContain('digantikan sepenuhnya');
      expect(w.body).not.toContain('photos will be replaced');
    });
  });

  describe('when one uploaded photo', () => {
    it('uses the singular "photo" form and requires acknowledgement', () => {
      const w = buildRegenerateWarning(1);
      expect(w.hasUploadedImages).toBe(true);
      expect(w.requiresAcknowledge).toBe(true);
      expect(w.body).toContain('1 uploaded photo will be replaced');
      // The plural "photos" must not leak when count === 1.
      expect(w.body).not.toContain('1 uploaded photos');
      expect(w.body).toContain('cannot be undone');
      expect(w.checkboxLabel).toBe('I understand my photos will be replaced');
    });
  });

  describe('when multiple uploaded photos', () => {
    it('uses the plural "photos" form with the actual count', () => {
      const w = buildRegenerateWarning(7);
      expect(w.hasUploadedImages).toBe(true);
      expect(w.body).toContain('7 uploaded photos will be replaced');
      expect(w.requiresAcknowledge).toBe(true);
    });
  });

  describe('defensive clamping', () => {
    it('treats negative counts as zero (no checkbox)', () => {
      // Could happen if a backend bug returns a negative count from a
      // filter expression. Better to fall back to the soft warning than
      // show "-3 uploaded photos will be replaced".
      const w = buildRegenerateWarning(-3);
      expect(w.hasUploadedImages).toBe(false);
      expect(w.requiresAcknowledge).toBe(false);
    });

    it('truncates fractional counts toward zero', () => {
      const w = buildRegenerateWarning(2.9);
      expect(w.body).toContain('2 uploaded photos');
    });

    it('treats NaN as zero', () => {
      const w = buildRegenerateWarning(NaN);
      expect(w.hasUploadedImages).toBe(false);
    });

    it('treats Infinity as zero', () => {
      const w = buildRegenerateWarning(Infinity);
      expect(w.hasUploadedImages).toBe(false);
    });
  });
});

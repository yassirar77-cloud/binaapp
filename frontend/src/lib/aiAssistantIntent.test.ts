import { describe, it, expect } from 'vitest';
import { detectIntent, detectWhatsappNumberChange } from './aiAssistantIntent';

describe('detectIntent', () => {
  describe('quick_edit — small, targeted changes', () => {
    const quickEditPrompts: [string, string][] = [
      ['Tukar warna button jadi merah', 'verb + colour element'],
      ['Tambah nombor telefon 0176119872', 'verb + phone element'],
      ['Tukar tajuk jadi Kedai Saya', 'verb + title element'],
      ['Buang seksyen footer', 'verb, short, no design term'],
      ['Tukar alamat kedai', 'verb + address element'],
      ['Tambah harga RM50 untuk nasi lemak', 'verb + price element'],
      ['Padam link Instagram', 'verb + link element'],
      ['Change phone number to 0123456789', 'english verb + phone'],
      ['Add email contact@kedai.com', 'english verb + email'],
      ['Tukar teks button', 'verb + text/button element'],
    ];

    it.each(quickEditPrompts)('classifies %j as quick_edit (%s)', (prompt) => {
      const result = detectIntent(prompt);
      expect(result.intent).toBe('quick_edit');
      expect(result.indicators.length).toBeGreaterThan(0);
      expect(result.reason).toBeTruthy();
    });
  });

  describe('full_regenerate — design / rebuild requests', () => {
    const fullRegeneratePrompts: [string, string][] = [
      ['Lagi modern', 'style word "modern"'],
      ['Buat semula dengan dark theme', 'explicit rebuild + design'],
      ['Jana semula laman web ini', 'explicit rebuild phrase'],
      ['Tukar tema kepada minimalis', 'design wins over verb'],
      ['Redesign the website to look professional', 'explicit redesign'],
      ['Saya nak rupa yang lebih playful dan colourful', 'design terms'],
      ['Make the overall design more traditional Malaysian feel with warm colours', 'long + design'],
      ['Rebuild this site with a clean minimal style', 'explicit rebuild + minimal'],
    ];

    it.each(fullRegeneratePrompts)(
      'classifies %j as full_regenerate (%s)',
      (prompt) => {
        const result = detectIntent(prompt);
        expect(result.intent).toBe('full_regenerate');
        expect(result.reason).toBeTruthy();
      }
    );
  });

  describe('ambiguous — defaults to full_regenerate (safe fallback)', () => {
    const ambiguousPrompts = [
      'Boleh tolong sikit',
      'Saya tidak pasti apa yang patut sekarang juga',
    ];

    it.each(ambiguousPrompts)('defaults %j to full_regenerate', (prompt) => {
      const result = detectIntent(prompt);
      expect(result.intent).toBe('full_regenerate');
      expect(result.indicators).toEqual([]);
    });
  });

  describe('rule precedence and edge cases', () => {
    it('treats a long prompt as full_regenerate even with quick-edit verbs', () => {
      const longPrompt =
        'Tukar warna semua button kepada merah dan juga tukar semua tajuk ' +
        'seksyen supaya nampak lebih besar dan jelas pada telefon';
      expect(longPrompt.length).toBeGreaterThan(80);
      expect(detectIntent(longPrompt).intent).toBe('full_regenerate');
    });

    it('lets design intent override a quick-edit verb', () => {
      // "tukar" is a quick-edit verb but "tema" is a design term → rebuild.
      expect(detectIntent('Tukar tema').intent).toBe('full_regenerate');
    });

    it('does not match "add" inside "address"', () => {
      // If \badd\b leaked, "alamat" English equivalent "address" alone
      // (no verb) should still classify via the element, not a false verb.
      const result = detectIntent('address');
      expect(result.intent).toBe('quick_edit');
      expect(result.indicators).toContain('address');
      expect(result.indicators).not.toContain('add');
    });

    it('handles empty input by defaulting to full_regenerate', () => {
      expect(detectIntent('').intent).toBe('full_regenerate');
      expect(detectIntent('   ').intent).toBe('full_regenerate');
    });

    it('detects a verbatim style-chip modifier appended by a chip tap', () => {
      // When the user taps the "Lagi modern" chip the modifier text is
      // appended to the prompt; that must route to full_regenerate.
      const prompt = 'Kedai nasi lemak. Make it more modern, clean, minimalist.';
      expect(detectIntent(prompt).intent).toBe('full_regenerate');
    });

    it('returns indicators and a reason for transparency', () => {
      const result = detectIntent('Tukar warna button');
      expect(result.indicators).toEqual(expect.arrayContaining(['tukar']));
      expect(typeof result.reason).toBe('string');
      expect(result.reason.length).toBeGreaterThan(0);
    });

    it('routes a WhatsApp element edit to quick_edit, never regenerate', () => {
      // Regression: 'whatsapp'/'wasap' were missing from the element list, so a
      // contact-field edit fell through to the credit-gated full_regenerate.
      expect(detectIntent('Buang butang whatsapp').intent).toBe('quick_edit');
      expect(detectIntent('tukar wasap').intent).toBe('quick_edit');
    });
  });

  describe('detectWhatsappNumberChange — credit-free contact path', () => {
    it('extracts the new number from WhatsApp-change prompts', () => {
      expect(detectWhatsappNumberChange('tukar whatsapp ke 0123456789')).toBe(
        '0123456789'
      );
      expect(detectWhatsappNumberChange('wasap baru 011-2345678')).toBe(
        '011-2345678'
      );
      expect(detectWhatsappNumberChange('WhatsApp +60123456789')).toBe(
        '+60123456789'
      );
    });

    it('intercepts even a long natural sentence (>80 chars)', () => {
      const longPrompt =
        'Tolong tukar nombor WhatsApp kedai saya kepada 011-2345 6789 ' +
        'sebab nombor lama dah tak guna lagi';
      expect(longPrompt.length).toBeGreaterThan(80);
      expect(detectWhatsappNumberChange(longPrompt)).toBe('011-2345 6789');
    });

    it('returns null when there is no number or no WhatsApp mention', () => {
      expect(detectWhatsappNumberChange('buang butang whatsapp')).toBeNull();
      expect(detectWhatsappNumberChange('tukar nombor telefon ke 0123456789')).toBeNull();
      expect(detectWhatsappNumberChange('tukar warna kepada biru')).toBeNull();
      expect(detectWhatsappNumberChange('')).toBeNull();
    });
  });
});

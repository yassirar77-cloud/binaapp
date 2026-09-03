import { describe, it, expect } from 'vitest';
import {
  BRIEF_EXAMPLES,
  DESIGN_BRIEF_MAX,
  FREEDOM_OPTIONS,
  appendBriefExample,
  buildDesignPayload,
  freedomLabel,
  isDesignFreedom,
  normalizeDesignBrief,
} from './designBrief';

describe('normalizeDesignBrief', () => {
  it('returns undefined for empty input', () => {
    expect(normalizeDesignBrief(undefined)).toBeUndefined();
    expect(normalizeDesignBrief(null)).toBeUndefined();
    expect(normalizeDesignBrief('   \n ')).toBeUndefined();
  });

  it('collapses whitespace and caps the length', () => {
    expect(normalizeDesignBrief('  gelap   dan  mewah \n\n\n\n emas ')).toBe(
      'gelap dan mewah\n\nemas'
    );
    expect(normalizeDesignBrief('x'.repeat(5000))).toHaveLength(DESIGN_BRIEF_MAX);
  });
});

describe('appendBriefExample', () => {
  it('starts a brief from an example', () => {
    expect(appendBriefExample('', 'Gelap dan mewah.')).toBe('Gelap dan mewah.');
  });

  it('joins with sentence punctuation', () => {
    expect(appendBriefExample('Ala kopitiam', 'Aksen emas.')).toBe('Ala kopitiam. Aksen emas.');
    expect(appendBriefExample('Ala kopitiam!', 'Aksen emas.')).toBe('Ala kopitiam! Aksen emas.');
  });

  it('does not add the same example twice', () => {
    const once = appendBriefExample('', 'Gelap dan mewah.');
    expect(appendBriefExample(once, 'gelap DAN mewah.')).toBe(once);
  });

  it('never exceeds the cap', () => {
    const long = 'a'.repeat(DESIGN_BRIEF_MAX - 3);
    expect(appendBriefExample(long, 'lagi banyak teks').length).toBeLessThanOrEqual(DESIGN_BRIEF_MAX);
  });
});

describe('buildDesignPayload', () => {
  it('defaults to designer freedom and drops an empty brief', () => {
    expect(buildDesignPayload({})).toEqual({ design_freedom: 'designer' });
    expect(buildDesignPayload({ designBrief: '   ' })).toEqual({ design_freedom: 'designer' });
  });

  it('carries a normalised brief, the freedom pick and the style', () => {
    expect(
      buildDesignPayload({ designBrief: '  gelap  mewah ', designFreedom: 'guided', designStyle: 'elegant' })
    ).toEqual({ design_brief: 'gelap mewah', design_freedom: 'guided', design_style: 'elegant' });
  });

  it('coerces an unknown freedom value to designer', () => {
    expect(buildDesignPayload({ designFreedom: 'wild' }).design_freedom).toBe('designer');
  });
});

describe('freedom options + labels', () => {
  it('offers exactly the two backend modes, designer first', () => {
    expect(FREEDOM_OPTIONS.map((o) => o.key)).toEqual(['designer', 'guided']);
    expect(isDesignFreedom('designer')).toBe(true);
    expect(isDesignFreedom('auto')).toBe(false);
  });

  it('labels fall back to the designer option', () => {
    expect(freedomLabel('guided')).toBe('Ikut sistem');
    expect(freedomLabel(null)).toBe('Designer bebas');
  });
});

describe('BRIEF_EXAMPLES', () => {
  it('has matching ids in both languages with short, non-empty text', () => {
    const ms = BRIEF_EXAMPLES.ms.map((e) => e.id);
    const en = BRIEF_EXAMPLES.en.map((e) => e.id);
    expect(ms).toEqual(en);
    for (const list of [BRIEF_EXAMPLES.ms, BRIEF_EXAMPLES.en]) {
      for (const example of list) {
        expect(example.text.length).toBeGreaterThan(10);
        expect(example.text.length).toBeLessThan(200);
        expect(example.label.length).toBeGreaterThan(0);
      }
    }
  });
});

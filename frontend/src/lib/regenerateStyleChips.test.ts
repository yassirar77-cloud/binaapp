import { describe, it, expect } from 'vitest';
import {
  STYLE_CHIPS,
  applyStyleChip,
  chipIsStillApplied,
  modifierFor,
} from './regenerateStyleChips';

describe('STYLE_CHIPS catalogue', () => {
  it('exposes the six required chips in the documented order', () => {
    expect(STYLE_CHIPS.map((c) => c.id)).toEqual([
      'modern',
      'traditional',
      'playful',
      'minimal',
      'dark',
      'light',
    ]);
  });

  it('every chip has a non-empty Malay label', () => {
    for (const chip of STYLE_CHIPS) {
      expect(chip.label.length).toBeGreaterThan(0);
    }
  });

  it('every modifier starts with a leading space so it joins cleanly', () => {
    for (const chip of STYLE_CHIPS) {
      expect(chip.modifier.startsWith(' ')).toBe(true);
    }
  });

  it('every modifier ends with a period', () => {
    for (const chip of STYLE_CHIPS) {
      expect(chip.modifier.trim().endsWith('.')).toBe(true);
    }
  });
});

describe('modifierFor', () => {
  it('returns the modifier text for a known chip id', () => {
    expect(modifierFor('modern')).toBe(
      ' Make it more modern, clean, minimalist.'
    );
  });

  it('returns empty string for null / undefined', () => {
    expect(modifierFor(null)).toBe('');
    expect(modifierFor(undefined)).toBe('');
  });
});

describe('applyStyleChip', () => {
  const desc = 'Restoran nasi lemak di Shah Alam';

  it('appends the modifier when no previous chip was selected', () => {
    const next = applyStyleChip(desc, null, 'modern');
    expect(next).toBe(
      'Restoran nasi lemak di Shah Alam Make it more modern, clean, minimalist.'
    );
  });

  it('replaces the previous modifier instead of stacking', () => {
    const afterModern = applyStyleChip(desc, null, 'modern');
    const afterDark = applyStyleChip(afterModern, 'modern', 'dark');
    // The modern modifier must be gone.
    expect(afterDark).not.toContain(
      'Make it more modern, clean, minimalist.'
    );
    // The dark modifier must be present once.
    expect(afterDark).toBe(
      'Restoran nasi lemak di Shah Alam Use a dark theme with high contrast.'
    );
  });

  it('strips the previous modifier when next chip is null', () => {
    const afterPlayful = applyStyleChip(desc, null, 'playful');
    const cleared = applyStyleChip(afterPlayful, 'playful', null);
    expect(cleared).toBe(desc);
  });

  it('does NOT silently strip an edited modifier (user retyped part)', () => {
    // User picked modern, then deleted ".clean, minimalist." part.
    const edited =
      'Restoran nasi lemak di Shah Alam Make it more modern';
    // Switching to dark must not corrupt the user-typed remainder.
    const after = applyStyleChip(edited, 'modern', 'dark');
    expect(after).toBe(
      'Restoran nasi lemak di Shah Alam Make it more modern Use a dark theme with high contrast.'
    );
  });

  it('treats empty / missing description safely', () => {
    expect(applyStyleChip('', null, 'modern')).toBe(
      ' Make it more modern, clean, minimalist.'
    );
    expect(applyStyleChip(undefined as unknown as string, null, 'modern')).toBe(
      ' Make it more modern, clean, minimalist.'
    );
  });

  it('clearing a chip on empty description stays empty', () => {
    expect(applyStyleChip('', null, null)).toBe('');
  });

  it('stacking-then-clearing leaves the original description intact', () => {
    let text = desc;
    text = applyStyleChip(text, null, 'modern');
    text = applyStyleChip(text, 'modern', 'traditional');
    text = applyStyleChip(text, 'traditional', 'playful');
    text = applyStyleChip(text, 'playful', null);
    expect(text).toBe(desc);
  });
});

describe('component-flow simulation', () => {
  /**
   * Mirrors the exact state-update sequence performed by the
   * StyleChipRow `onSelect` handler in editor/[id]/page.tsx. The
   * project's vitest setup uses the node environment (no jsdom /
   * testing-library), so a click-based component test would require
   * a new dev dep — the prompt forbids that. Reproducing the handler's
   * logic here gives equivalent coverage: prove that a tap-tap-retap
   * sequence updates the textarea value the same way the real handler
   * does.
   */
  function simulateChipTap(
    state: { description: string; selectedChipId: StyleChipId | null },
    tappedId: StyleChipId
  ) {
    const effectivePrev = chipIsStillApplied(
      state.description,
      state.selectedChipId
    )
      ? state.selectedChipId
      : null;
    // Re-tap = clear; otherwise switch.
    const nextId = tappedId === state.selectedChipId ? null : tappedId;
    return {
      description: applyStyleChip(state.description, effectivePrev, nextId),
      selectedChipId: nextId,
    };
  }

  type StyleChipId = (typeof STYLE_CHIPS)[number]['id'];

  it('first tap appends the modifier and activates the chip', () => {
    const initial = {
      description: 'Restoran nasi lemak',
      selectedChipId: null as StyleChipId | null,
    };
    const after = simulateChipTap(initial, 'modern');
    expect(after.selectedChipId).toBe('modern');
    expect(after.description).toContain(
      'Make it more modern, clean, minimalist.'
    );
  });

  it('tapping a different chip replaces the modifier (no stacking)', () => {
    let state = {
      description: 'Restoran nasi lemak',
      selectedChipId: null as StyleChipId | null,
    };
    state = simulateChipTap(state, 'modern');
    state = simulateChipTap(state, 'dark');

    expect(state.selectedChipId).toBe('dark');
    // Modern modifier is fully gone.
    expect(state.description).not.toContain('modern, clean, minimalist');
    // Dark modifier appears exactly once.
    const occurrences = state.description.split(
      'Use a dark theme with high contrast.'
    ).length - 1;
    expect(occurrences).toBe(1);
  });

  it('re-tapping the active chip clears it and removes the modifier', () => {
    let state = {
      description: 'Cafe Bandar',
      selectedChipId: null as StyleChipId | null,
    };
    state = simulateChipTap(state, 'playful');
    expect(state.selectedChipId).toBe('playful');

    state = simulateChipTap(state, 'playful');
    expect(state.selectedChipId).toBe(null);
    expect(state.description).toBe('Cafe Bandar');
  });

  it('rapid switching across four chips never stacks modifiers', () => {
    let state = {
      description: 'Salon kecantikan',
      selectedChipId: null as StyleChipId | null,
    };
    for (const id of ['modern', 'traditional', 'playful', 'minimal'] as StyleChipId[]) {
      state = simulateChipTap(state, id);
    }
    expect(state.selectedChipId).toBe('minimal');
    // Only the minimal modifier should remain.
    expect(state.description).toBe(
      'Salon kecantikan Make it more minimal, lots of white space, simple typography.'
    );
    // None of the earlier modifiers should leak through.
    expect(state.description).not.toContain('modern');
    expect(state.description).not.toContain('traditional');
    expect(state.description).not.toContain('playful');
  });

  it('respects user edits — modifier left as-is if no longer verbatim', () => {
    // User picks "modern", then manually deletes part of the modifier,
    // then taps "dark". The handler must NOT strip the now-corrupted
    // modern text (it doesn't match verbatim), and must append "dark"
    // alongside it. The "modern" chip's selected state is irrelevant
    // because the page's onChange handler also flips selectedChipId to
    // null once the modifier no longer matches.
    let state = {
      description: 'Salon Make it more modern, clean', // user trimmed ", minimalist."
      selectedChipId: 'modern' as StyleChipId | null,
    };
    state = simulateChipTap(state, 'dark');
    expect(state.selectedChipId).toBe('dark');
    expect(state.description).toBe(
      'Salon Make it more modern, clean Use a dark theme with high contrast.'
    );
  });
});

describe('chipIsStillApplied', () => {
  it('returns true when the modifier text is verbatim in the description', () => {
    const text = 'Cafe Make it more playful, colourful, and fun.';
    expect(chipIsStillApplied(text, 'playful')).toBe(true);
  });

  it('returns false when the modifier has been partially edited', () => {
    const text = 'Cafe Make it more playful and fun';
    expect(chipIsStillApplied(text, 'playful')).toBe(false);
  });

  it('returns false for null chip id', () => {
    expect(chipIsStillApplied('whatever', null)).toBe(false);
  });

  it('returns false for empty description', () => {
    expect(chipIsStillApplied('', 'modern')).toBe(false);
  });
});

/**
 * Style hint chips for the regenerate flow.
 *
 * Tapping a chip appends a short modifier sentence to the description
 * that gets sent to the LLM. Chips are radio-style (single selection)
 * so switching chips replaces the previous modifier instead of stacking.
 *
 * Why the modifier text is English while labels are Malay:
 *   - Labels show in the UI; existing copy is Bahasa Melayu.
 *   - Modifier text goes straight to the LLM, which has stronger
 *     instruction-following in English. Mixing matches what the
 *     existing strict prompt does (English directives, Malay content).
 */

export interface StyleChip {
  /** Stable id used by aria-pressed comparisons + tests. */
  id: StyleChipId;
  /** Emoji rendered before the label. Pure decoration. */
  icon: string;
  /** Bahasa Melayu label shown in the UI. */
  label: string;
  /** English modifier appended to the description. */
  modifier: string;
}

export type StyleChipId =
  | 'modern'
  | 'traditional'
  | 'playful'
  | 'minimal'
  | 'dark'
  | 'light';

export const STYLE_CHIPS: readonly StyleChip[] = [
  {
    id: 'modern',
    icon: '🎨',
    label: 'Lagi modern',
    modifier: ' Make it more modern, clean, minimalist.',
  },
  {
    id: 'traditional',
    icon: '🏛️',
    label: 'Lagi tradisional',
    modifier: ' Make it warmer and more traditional Malaysian feel.',
  },
  {
    id: 'playful',
    icon: '✨',
    label: 'Lagi playful',
    modifier: ' Make it more playful, colourful, and fun.',
  },
  {
    id: 'minimal',
    icon: '🖤',
    label: 'Lagi minimal',
    modifier:
      ' Make it more minimal, lots of white space, simple typography.',
  },
  {
    id: 'dark',
    icon: '🌙',
    label: 'Dark theme',
    modifier: ' Use a dark theme with high contrast.',
  },
  {
    id: 'light',
    icon: '🌞',
    label: 'Light theme',
    modifier: ' Use a bright light theme.',
  },
] as const;

/** Look up the modifier text for a chip id, or `''` if unknown. */
export function modifierFor(id: StyleChipId | null | undefined): string {
  if (!id) return '';
  const chip = STYLE_CHIPS.find((c) => c.id === id);
  return chip ? chip.modifier : '';
}

/**
 * Apply (or swap) a chip's modifier in the description.
 *
 * Behaviour:
 *   - If `previousChipId` is set, its modifier text is stripped first.
 *   - The new chip's modifier is appended verbatim. We do NOT auto-trim
 *     trailing whitespace — the modifier strings start with a single
 *     space on purpose so they sit cleanly after user-typed text.
 *   - If `nextChipId` is null (chip cleared), only the previous modifier
 *     is stripped.
 *
 * If the user has manually edited the previous modifier (e.g. retyped
 * part of it), `previousModifier` won't match verbatim and won't be
 * stripped — we never silently mutate user-typed text.
 */
export function applyStyleChip(
  description: string,
  previousChipId: StyleChipId | null,
  nextChipId: StyleChipId | null
): string {
  let next = description ?? '';
  const previousModifier = modifierFor(previousChipId);
  if (previousModifier && next.includes(previousModifier)) {
    next = next.split(previousModifier).join('');
  }
  const nextModifier = modifierFor(nextChipId);
  if (nextModifier) {
    next = next + nextModifier;
  }
  return next;
}

/**
 * Detect whether the textarea still contains the chip's modifier
 * verbatim. Used to de-highlight the chip when the user edits the
 * description in a way that no longer matches.
 */
export function chipIsStillApplied(
  description: string,
  chipId: StyleChipId | null
): boolean {
  if (!chipId) return false;
  const modifier = modifierFor(chipId);
  if (!modifier) return false;
  return (description ?? '').includes(modifier);
}

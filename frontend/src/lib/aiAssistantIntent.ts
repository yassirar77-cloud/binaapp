/**
 * Intent detection for the unified "AI Assistant" in the editor.
 *
 * The editor exposes a single prompt box. Depending on what the user
 * types we route to one of two very different backends:
 *
 *   - `quick_edit`      → POST /api/edit-html (fast, in-place tweak,
 *                          NOT persisted until the user hits Simpan)
 *   - `full_regenerate` → PATCH /api/v1/websites/{id}/regenerate
 *                          (slow, rebuilds the whole site, burns one
 *                          AI-hero credit, persisted server-side)
 *
 * Because picking the wrong branch is expensive (a full regenerate
 * costs a credit and replaces the whole page), the heuristics here are
 * deliberately biased: when the signal is weak or contradictory we
 * default to `full_regenerate`. A full regenerate is the safer fallback
 * because it covers every kind of request, increments quota correctly,
 * and persists — whereas mis-routing a "redesign" into the quick-edit
 * path would silently produce a poor result the user can't undo.
 *
 * This is a PURE module (no React, no network) so it can be unit-tested
 * in the node-env vitest setup without rendering the editor page.
 */

import { STYLE_CHIPS } from './regenerateStyleChips';

export type Intent = 'quick_edit' | 'full_regenerate';

export interface IntentResult {
  /** Which backend flow to use. */
  intent: Intent;
  /** Short Bahasa Melayu explanation shown in the UI tooltip. */
  reason: string;
  /** The matched signal tokens — surfaced in the tooltip for transparency. */
  indicators: string[];
}

/** Above this length a prompt is treated as a full rebuild request. */
const LONG_PROMPT_THRESHOLD = 80;

/**
 * Action verbs that signal a small, targeted change. Single words —
 * matched on word boundaries so `add` does not match inside `address`.
 */
const QUICK_EDIT_VERBS = [
  'tukar',
  'ubah',
  'tambah',
  'buang',
  'padam',
  'change',
  'replace',
  'add',
  'remove',
];

/**
 * Concrete UI elements a quick edit usually targets. Presence of any of
 * these (even without a verb) leans toward a quick edit.
 */
const SPECIFIC_ELEMENTS = [
  'button',
  'butang',
  'warna',
  'colour',
  'color',
  'text',
  'teks',
  'title',
  'tajuk',
  'nombor',
  'telefon',
  'phone',
  'alamat',
  'address',
  'harga',
  'price',
  'link',
  'pautan',
  'email',
  'emel',
];

/**
 * Words that signal an overall design / look-and-feel change. Any match
 * forces `full_regenerate` even if a quick-edit verb is also present
 * ("tukar tema" = change the theme = full rebuild, not a quick edit).
 */
const DESIGN_TERMS = [
  'design',
  'style',
  'gaya',
  'theme',
  'tema',
  'vibe',
  'feel',
  'look',
  'rupa',
  'modern',
  'traditional',
  'tradisional',
  'playful',
  'minimal',
  'minimalis',
  'dark',
  'light',
  'gelap',
  'cerah',
  'terang',
  'colourful',
  'colorful',
];

/**
 * Phrases where the user explicitly asks for a rebuild. Multi-word, so
 * matched as substrings rather than word-boundary tokens.
 */
const EXPLICIT_REGENERATE = [
  'rebuild',
  'rewrite',
  'regenerate',
  'redesign',
  'revamp',
  'buat semula',
  'jana semula',
  'bina semula',
  'reka semula',
];

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Find which of `tokens` appear in `haystack`. Multi-word tokens are
 * matched as plain substrings; single words are matched on ASCII word
 * boundaries so short verbs like `add` don't match inside other words.
 */
function findMatches(haystack: string, tokens: string[]): string[] {
  const found: string[] = [];
  for (const token of tokens) {
    if (token.includes(' ')) {
      if (haystack.includes(token)) found.push(token);
    } else {
      const re = new RegExp(`\\b${escapeRegExp(token)}\\b`, 'i');
      if (re.test(haystack)) found.push(token);
    }
  }
  return found;
}

/** Detect whether the prompt contains a verbatim style-chip modifier. */
function matchedStyleChipModifiers(haystack: string): string[] {
  const found: string[] = [];
  for (const chip of STYLE_CHIPS) {
    const mod = chip.modifier.trim().toLowerCase();
    if (mod && haystack.includes(mod)) found.push(chip.id);
  }
  return found;
}

/**
 * Classify a prompt into `quick_edit` or `full_regenerate`.
 *
 * Decision order (first match wins):
 *   1. Explicit rebuild phrase            → full_regenerate
 *   2. Style-chip modifier / design term  → full_regenerate
 *   3. Prompt longer than 80 chars        → full_regenerate
 *   4. (verb AND short) OR specific element → quick_edit
 *   5. Otherwise (weak/ambiguous signal)  → full_regenerate (safe default)
 */
export function detectIntent(prompt: string): IntentResult {
  const text = (prompt ?? '').trim();
  const lower = text.toLowerCase();

  // 1. Explicit rebuild request.
  const explicit = findMatches(lower, EXPLICIT_REGENERATE);
  if (explicit.length > 0) {
    return {
      intent: 'full_regenerate',
      reason: 'Anda meminta laman web dibina semula sepenuhnya.',
      indicators: explicit,
    };
  }

  // 2. Design / style-chip intent.
  const chipMatches = matchedStyleChipModifiers(lower);
  const designMatches = findMatches(lower, DESIGN_TERMS);
  if (chipMatches.length > 0 || designMatches.length > 0) {
    return {
      intent: 'full_regenerate',
      reason: 'Perubahan gaya atau reka bentuk keseluruhan — AI akan jana semula laman web.',
      indicators: [...chipMatches, ...designMatches],
    };
  }

  // 3. Long prompts are treated as a full rebuild.
  if (text.length > LONG_PROMPT_THRESHOLD) {
    return {
      intent: 'full_regenerate',
      reason: `Penerangan panjang (${text.length} aksara) — lebih sesuai untuk jana semula.`,
      indicators: [`>${LONG_PROMPT_THRESHOLD} aksara`],
    };
  }

  // 4. Quick, targeted edit.
  const verbs = findMatches(lower, QUICK_EDIT_VERBS);
  const elements = findMatches(lower, SPECIFIC_ELEMENTS);
  const isShort = text.length <= LONG_PROMPT_THRESHOLD;
  if ((verbs.length > 0 && isShort) || elements.length > 0) {
    return {
      intent: 'quick_edit',
      reason: 'Perubahan kecil dan spesifik — AI akan edit terus tanpa jana semula.',
      indicators: [...verbs, ...elements],
    };
  }

  // 5. Ambiguous — default to the safer full rebuild.
  return {
    intent: 'full_regenerate',
    reason: 'Arahan tidak jelas — guna jana semula penuh untuk keputusan terbaik.',
    indicators: [],
  };
}

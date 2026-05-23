/**
 * Helpers for the regenerate-confirm modal in the editor.
 *
 * Keeping the count-derived strings + checkbox gating in pure functions
 * lets us unit-test them without rendering the editor page.
 */

export interface RegenerateWarning {
  /** Strong, image-aware warning when the website has uploaded photos. */
  hasUploadedImages: boolean;
  /** Headline shown at the top of the modal. */
  headline: string;
  /** Body paragraph — fully composed, ready to render. */
  body: string;
  /** Label for the acknowledge checkbox. Empty string when none needed. */
  checkboxLabel: string;
  /** Whether the confirm button should require a checkbox tick. */
  requiresAcknowledge: boolean;
}

/**
 * Build the warning content for the regenerate confirm modal.
 *
 * - 0 uploaded photos → existing soft warning, no checkbox.
 * - ≥1 uploaded photos → image-aware warning + required checkbox.
 *
 * Negative or non-finite counts are clamped to 0 (defensive — the count
 * comes from a network call that might 500 or return garbage).
 */
export function buildRegenerateWarning(
  uploadedImageCount: number
): RegenerateWarning {
  const count = Number.isFinite(uploadedImageCount)
    ? Math.max(0, Math.floor(uploadedImageCount))
    : 0;

  if (count === 0) {
    return {
      hasUploadedImages: false,
      headline: 'Sahkan regenerate?',
      body:
        'HTML semasa akan digantikan sepenuhnya dengan versi baru ' +
        'daripada AI. Edit manual yang anda buat akan hilang. Ini juga ' +
        'menggunakan satu kredit AI hero dari plan langganan anda.',
      checkboxLabel: '',
      requiresAcknowledge: false,
    };
  }

  const photoWord = count === 1 ? 'photo' : 'photos';
  return {
    hasUploadedImages: true,
    headline: 'Sahkan regenerate?',
    body:
      `⚠️ Your ${count} uploaded ${photoWord} will be replaced with ` +
      `AI-generated images. This cannot be undone. Edit manual yang ` +
      `anda buat juga akan hilang. Ini menggunakan satu kredit AI hero ` +
      `dari plan langganan anda.`,
    checkboxLabel: 'I understand my photos will be replaced',
    requiresAcknowledge: true,
  };
}

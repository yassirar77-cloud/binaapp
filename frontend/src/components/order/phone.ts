/**
 * Malaysian phone-number helpers for the customer-facing /order flow.
 *
 * Storage convention (matches chat.py and the existing order flow):
 *   - 10-digit Malaysian local format, digits only, e.g. `0176119872`
 *   - The leading `0` IS included
 *   - Country code (+60) is NOT stored — it's a UI affordance only
 *
 * Display convention:
 *   - User types into a field locked with a `+60` prefix
 *   - Digits-as-typed get formatted live: `12-345 6789`
 *   - The `0` prefix is added back when we save / send to the backend
 */

/** Strip every non-digit and trim whitespace. */
export function digitsOnly(raw: string): string {
  return (raw || '').replace(/\D/g, '')
}

/**
 * Format the digits the user has typed (with NO leading 0 — they're
 * implied by the `+60` prefix in the UI) for live display.
 *
 *   2  → `12`
 *   3  → `123`
 *   5  → `12-345`
 *   9  → `12-345 6789`
 */
export function formatPhoneDisplay(typed: string): string {
  const d = digitsOnly(typed)
  if (d.length <= 2) return d
  if (d.length <= 5) return `${d.slice(0, 2)}-${d.slice(2)}`
  return `${d.slice(0, 2)}-${d.slice(2, 5)} ${d.slice(5, 9)}`
}

/**
 * Convert what the user typed (digits without the leading 0, since the
 * UI shows +60 separately) into the storage form `0XXXXXXXXX`.
 */
export function toStorageFormat(typed: string): string {
  const d = digitsOnly(typed)
  // If the user pasted with a leading 0 (because they ignored the +60
  // prefix), keep it. Otherwise prepend.
  return d.startsWith('0') ? d : `0${d}`
}

/**
 * Inverse of `toStorageFormat` — strip the leading 0 from a stored
 * phone so it can be displayed inside the +60-prefixed input.
 */
export function fromStorageFormat(stored: string): string {
  const d = digitsOnly(stored)
  return d.startsWith('0') ? d.slice(1) : d
}

/**
 * A typed phone is "valid enough to look up" once the user has entered
 * 9 digits (the local Malaysian mobile format past the leading 0).
 */
export function isValidTyped(typed: string): boolean {
  return digitsOnly(typed).length >= 9
}

/** Initials for the returning-customer avatar — first letters of up to 2 words. */
export function nameInitials(name: string): string {
  return (name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')
}

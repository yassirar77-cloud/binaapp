// Phone number helpers — kept in a dedicated file because the WA formatter
// is the one piece of glue most likely to regress (the old page.tsx had a
// double-`60` bug for numbers already starting with `60`).

/** Strips non-digits, then normalizes a Malaysian mobile number to the
 *  E.164-compatible form expected by wa.me (no `+`, country code first).
 *
 *  Examples:
 *    "+60 12-345 6789"  → "60123456789"
 *    "0123456789"        → "60123456789"
 *    "60123456789"       → "60123456789"   (idempotent, fixes prior bug)
 *    "123456789"         → "60123456789"   (no leading 0, treat as MY)
 */
export function formatPhoneForWA(phone: string): string {
  const digits = (phone || '').replace(/\D/g, '');
  if (!digits) return '';
  if (digits.startsWith('60')) return digits;
  if (digits.startsWith('0')) return '60' + digits.slice(1);
  return '60' + digits;
}

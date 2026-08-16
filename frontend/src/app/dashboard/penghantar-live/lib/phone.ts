// Malaysian phone normalization for tel:/wa.me links.
// Same logic as the rider app's formatPhoneForWA — the previous cleanPhone
// here only stripped non-digits, so local "012-345 6789" numbers produced
// broken wa.me/0123456789 links (wa.me requires country code, no plus).

/** Strips non-digits and prefixes the MY country code where missing.
 *  Idempotent for numbers already starting with 60. */
export function formatPhoneForWA(phone: string | null | undefined): string {
  const digits = (phone || '').replace(/\D/g, '');
  if (!digits) return '';
  if (digits.startsWith('60')) return digits;
  if (digits.startsWith('0')) return '60' + digits.slice(1);
  return '60' + digits;
}

/** Digits-only form for tel: links (keeps local formats dialable). */
export function cleanPhoneDigits(phone: string | null | undefined): string {
  return (phone || '').replace(/\D/g, '');
}

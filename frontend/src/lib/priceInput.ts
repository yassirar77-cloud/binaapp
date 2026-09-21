/**
 * Tidy a price as typed into the create page's menu rows before it is sent.
 *
 * The field's onChange keeps the input to digits and one dot, at most two
 * decimals — so "24.", ".9" and a lone "." can all be sitting in a row when
 * the merchant presses Generate. The backend refuses anything it cannot read
 * as a number and the whole generation stops with "invalid_price", for a
 * value any human reads as 24.00. Settle those here.
 *
 * Pure module so the rules are unit-testable.
 */
export function normalizePriceInput(raw: string | null | undefined): string {
  let s = String(raw ?? '').trim().replace(/,/g, '.');
  if (!/\d/.test(s)) return '';            // "", ".", "RM" — no price
  if (s.startsWith('.')) s = '0' + s;      // ".9" → "0.9"
  if (s.endsWith('.')) s = s.slice(0, -1); // "24." → "24"
  return s;
}

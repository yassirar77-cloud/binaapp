import { redirect } from 'next/navigation'

/**
 * Root of the customer-facing /order tree. Always sends users to the
 * identify page; the identify page itself decides whether to pre-fill
 * from localStorage and short-circuit to "returning customer" state.
 *
 * Per the Q3 product decision (always show identify, never auto-skip):
 * shared devices are common in Malaysia, so we route users through the
 * phone screen on every visit even when localStorage has a saved phone.
 */
export default function OrderRoot() {
  redirect('/order/identify')
}

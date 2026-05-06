/**
 * Maps the backend `OrderStatus` enum (10 granular states) onto the
 * 5-step visual progress used by the customer-facing tracking page.
 *
 * Backend enum (from delivery_schemas.py):
 *   pending, confirmed, assigned, preparing, ready, picked_up,
 *   delivering, delivered, completed, cancelled, rejected
 *
 * Visual steps:
 *   0  Diterima             (received)
 *   1  Sedang disediakan    (preparing)
 *   2  Menunggu pickup      (waiting for pickup)
 *   3  Dalam perjalanan     (out for delivery)
 *   4  Sampai               (delivered)
 *
 * Cancelled / rejected orders are flagged terminal but with stepIndex
 * stuck at the last reached step — the UI surfaces a separate
 * "dibatalkan" banner rather than progressing further.
 */

export type BackendOrderStatus =
  | 'pending'
  | 'confirmed'
  | 'assigned'
  | 'preparing'
  | 'ready'
  | 'picked_up'
  | 'delivering'
  | 'delivered'
  | 'completed'
  | 'cancelled'
  | 'rejected'

export type VisualStepId = 'received' | 'preparing' | 'ready' | 'delivery' | 'delivered'

export interface VisualStep {
  id: VisualStepId
  label: string
}

export const VISUAL_STEPS: VisualStep[] = [
  { id: 'received', label: 'Diterima' },
  { id: 'preparing', label: 'Sedang disediakan' },
  { id: 'ready', label: 'Menunggu pickup' },
  { id: 'delivery', label: 'Dalam perjalanan' },
  { id: 'delivered', label: 'Sampai' },
]

/** Maps a backend status to its visual step index (0..4). */
export function statusToStepIndex(status: BackendOrderStatus | string | null | undefined): number {
  switch (status) {
    case 'pending':
    case 'confirmed':
    case 'assigned':
      return 0
    case 'preparing':
      return 1
    case 'ready':
      return 2
    case 'picked_up':
    case 'delivering':
      return 3
    case 'delivered':
    case 'completed':
      return 4
    case 'cancelled':
    case 'rejected':
      // Stay where the order was; the UI shows a separate cancellation banner.
      return 0
    default:
      return 0
  }
}

/** True for any status where polling can stop. */
export function isTerminalStatus(status: BackendOrderStatus | string | null | undefined): boolean {
  return (
    status === 'delivered' ||
    status === 'completed' ||
    status === 'cancelled' ||
    status === 'rejected'
  )
}

/** True only for a happy-path delivered/completed order. */
export function isDeliveredStatus(status: BackendOrderStatus | string | null | undefined): boolean {
  return status === 'delivered' || status === 'completed'
}

/** True when we should render the live tracking map (rider en-route). */
export function shouldShowMap(status: BackendOrderStatus | string | null | undefined): boolean {
  return status === 'picked_up' || status === 'delivering'
}

/** Polling interval — tighter once the rider is en-route. */
export function pollingIntervalMs(status: BackendOrderStatus | string | null | undefined): number {
  return shouldShowMap(status) ? 10_000 : 15_000
}

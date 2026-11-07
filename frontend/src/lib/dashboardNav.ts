/**
 * One nav config for the dashboard's two menus.
 *
 * The header's ☰ menu (DashboardHeader) and the left drawer opened from the
 * logo on mobile (MobileDashboard) kept separate lists; the drawer's had
 * drifted to routes that no longer exist (/websites, /orders, /delivery,
 * /menu, /analytics — all 404). Both now render these items.
 */

export interface DashboardNavItem {
  label: string
  href: string
  /** Shows the new-orders count. */
  ordersBadge?: boolean
  /** Rider/GPS delivery ops — Bisnes (pro) plan only. Locked on Permulaan. */
  requiresRiders?: boolean
}

export const DASHBOARD_NAV_ITEMS: readonly DashboardNavItem[] = [
  { label: 'Papan Pemuka', href: '/dashboard' },
  { label: 'Website Saya', href: '/my-projects' },
  { label: 'Pesanan', href: '/pesanan', ordersBadge: true },
  { label: 'Chat', href: '/chat' },
  { label: 'Penghantar', href: '/rider', requiresRiders: true },
  { label: 'Penghantaran', href: '/dashboard/penghantaran' },
  { label: 'Penghantar Live', href: '/dashboard/penghantar-live', requiresRiders: true },
  { label: 'Menu', href: '/menu-designer' },
  { label: 'Analitik', href: '/dashboard/analitik' },
]

/** Account links, shown under the nav in both menus (plus Log Keluar). */
export const ACCOUNT_NAV_ITEMS: readonly DashboardNavItem[] = [
  { label: 'Profil', href: '/profile' },
  { label: 'Langganan', href: '/subscription' },
]

export const LOGOUT_LABEL = 'Log Keluar'

/** Whether a nav item is the current page. */
export function isActive(href: string, pathname: string | null | undefined): boolean {
  return !!pathname && pathname === href
}

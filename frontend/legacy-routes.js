/**
 * Old dashboard routes → the pages that replaced them.
 *
 * The mobile dashboard's left drawer linked to routes that no longer exist
 * (Pesanan → /orders was a 404). Both menus now read one config
 * (src/lib/dashboardNav.ts); these redirects catch bookmarks and any old
 * link still out there. Exact paths only: /delivery/:websiteId and
 * /analytics/:id are live customer/report pages and must not move.
 *
 * Plain CommonJS so next.config.js can require it.
 */
const LEGACY_DASHBOARD_ROUTES = {
  '/websites': '/my-projects',
  '/orders': '/pesanan',
  '/delivery': '/dashboard/penghantaran',
  '/menu': '/menu-designer',
  '/analytics': '/dashboard/analitik',
}

module.exports = { LEGACY_DASHBOARD_ROUTES }

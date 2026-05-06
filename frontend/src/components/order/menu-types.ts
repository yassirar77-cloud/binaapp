/**
 * Customer-flow menu types — the normalized shape consumed by the
 * /order/menu page after running through the menu-api normalizer.
 *
 * The backend speaks snake_case (`category_id`, `image_url`, `is_available`).
 * Everything in this file is camelCase and only carries the fields the UI
 * actually uses. New fields get added when a feature actually needs them.
 */

export interface MenuCategory {
  /** UUID from `menu_categories.id`, or the synthetic `'all'` pseudo-category. */
  id: string
  /** Display name. e.g. `Nasi`, `Roti & Murtabak`. */
  name: string
}

export interface MenuItem {
  /** UUID from `menu_items.id`. Used as cart item id and order_item.menu_item_id. */
  id: string
  /** UUID of parent category, or null for uncategorized items (rendered only under `Semua`). */
  categoryId: string | null
  name: string
  description: string
  /** RM price, normalized to a JS number. */
  price: number
  /** Image URL, or empty string when the restaurant hasn't uploaded one. */
  image: string
  /** Whether the item is currently orderable. The backend already filters
   *  unavailable items at query time, so this is `true` for everything in
   *  the response — kept on the type so we can render a sold-out overlay
   *  if the backend ever loosens the filter. */
  isAvailable: boolean
  isPopular: boolean
}

/** Normalized menu payload — what the UI consumes. */
export interface MenuData {
  /**
   * Categories in the order the restaurant configured them, with the
   * synthetic `{id: 'all', name: 'Semua'}` prepended at index 0.
   */
  categories: MenuCategory[]
  items: MenuItem[]
}

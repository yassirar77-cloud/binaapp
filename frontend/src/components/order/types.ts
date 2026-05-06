/**
 * Shared types for the customer-facing /order flow.
 *
 * Convention: camelCase in TS. The DB column convention is snake_case
 * (e.g. websites.brand_primary). When real subdomain resolution lands
 * (PR 2+), add a mapper at the data-fetch boundary.
 */

export type RestaurantStatus = 'open' | 'closed' | 'busy'

export interface RestaurantTheme {
  /**
   * UUID of the underlying `websites` row. Used to scope API calls
   * (customer lookup, menu fetch, order placement) to this restaurant.
   *
   * TODO(restaurant): Replace the hardcoded mitora UUID in DEFAULT_RESTAURANT
   * with real subdomain resolution from middleware (e.g. pelita.binaapp.my
   * resolves to websites.slug='pelita').
   */
  websiteId: string

  /** Full display name. e.g. "Nasi Kandar Pelita" */
  name: string
  /** Short name for headlines. e.g. "Pelita" */
  short: string
  /** 2-3 char monogram for the logo mark. e.g. "NP" */
  initials: string
  /** Cuisine eyebrow. e.g. "Mamak · Indian Muslim" */
  cuisine: string
  /** Open/closed state shown via pill in header. */
  status: RestaurantStatus

  /** Primary brand color. Used for buttons, accents, focus rings. */
  brandPrimary: string
  /** Hover variant of the primary color. */
  brandPrimaryHover: string
  /** Foreground color rendered on top of brandPrimary fills. */
  brandPrimaryFg: string
  /**
   * RESERVED. Defined in theme.css but not used by any current customer-flow
   * page. Kept on the type for future use (e.g. accent borders, illustration).
   */
  brandSecondary: string
  /**
   * RESERVED. Optional URL for an image-logo restaurant. Currently every
   * restaurant uses the initials mark only.
   */
  brandLogoUrl?: string
}

export interface CartItem {
  /** Menu item UUID — matches `menu_items.id` from the backend. */
  id: string
  name: string
  price: number
  qty: number
  img?: string
}

/**
 * Customer identity captured by the phone-identification page.
 *
 * Stored in a separate Zustand store + localStorage key (`binaapp_customer`)
 * because cart and customer have different lifecycles: the cart clears
 * after order placement, but the customer record persists for repeat
 * orders.
 */
export interface Customer {
  /** Server-side UUID from `website_customers.id`. Null until first order. */
  id: string | null
  /** 10-digit Malaysian local format, digits only — e.g. `0176119872`. */
  phone: string
  /** Display name from `website_customers.name`. Empty until customer fills it in. */
  name: string
  /** Last saved delivery address from `website_customers.address`. Empty for new customers. */
  address: string
  /** ISO timestamp of when this identity was captured. */
  savedAt: string
}

/** Response shape from `GET /api/v1/customers/lookup`. */
export type CustomerLookupResponse =
  | { exists: false }
  | {
      exists: true
      customer: {
        id: string
        name: string
        address: string
        phone: string
      }
    }
